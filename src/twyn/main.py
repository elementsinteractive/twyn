import logging
import re
from typing import Optional

from rich.logging import RichHandler
from rich.progress import track

from twyn.base.constants import (
    DEFAULT_SELECTOR_METHOD,
    SELECTOR_METHOD_MAPPING,
    AvailableLoggingLevels,
)
from twyn.core.config_handler import ConfigHandler
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.similarity.algorithm import EditDistance, SimilarityThreshold
from twyn.trusted_packages import TopPyPiReference
from twyn.trusted_packages.selectors import AbstractSelector
from twyn.trusted_packages.trusted_packages import (
    TrustedPackages,
    TyposquatCheckResult,
)

logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
logger = logging.getLogger()


def check_dependencies(
    config_file: Optional[str],
    dependency_file: str,
    selector_method: str,
    verbosity: AvailableLoggingLevels = AvailableLoggingLevels.none,
) -> bool:
    """Check if dependencies could be typosquats."""
    config = get_configuration(config_file, dependency_file, selector_method, verbosity)
    trusted_packages = TrustedPackages(
        names=TopPyPiReference().get_packages(),
        algorithm=EditDistance(),
        selector=get_candidate_selector(config.selector_method),
        threshold_class=SimilarityThreshold,
    )
    normalized_allowlist_packages = normalize_packages(config.allowlist)
    dependencies = get_parsed_dependencies(config.dependency_file)
    normalized_dependencies = normalize_packages(dependencies)

    errors: list[TyposquatCheckResult] = []
    for dependency in track(normalized_dependencies, description="Processing..."):
        if dependency in normalized_allowlist_packages:
            logger.info(f"Dependency {dependency} is in the allowlist")
            continue

        logger.info(f"Analyzing {dependency}")
        if dependency not in trusted_packages and (
            typosquat_results := trusted_packages.get_typosquat(dependency)
        ):
            errors.append(typosquat_results)

    for possible_typosquats in errors:
        logger.error(
            f"Possible typosquat detected: `{possible_typosquats.candidate_dependency}`, "
            f"did you mean any of [{', '.join(possible_typosquats.similar_dependencies)}]?"
        )

    return bool(errors)


def get_configuration(
    config_file: Optional[str],
    dependency_file: str,
    selector_method: str,
    verbosity: AvailableLoggingLevels,
) -> ConfigHandler:
    """Read configuration and return configuration object.

    Selects the appropriate values based on priorities between those in the file, and those directly provided.
    """
    # Read config from file
    config = ConfigHandler(file_path=config_file, enforce_file=False)

    # Set logging level according to priority order
    logging_level: AvailableLoggingLevels = get_logging_level(
        logging_level=verbosity,
        config_logging_level=config.logging_level,
    )
    set_logging_level(logging_level)
    config.logging_level = logging_level.value

    # Set selector method according to priority order
    config.selector_method = (
        selector_method or config.selector_method or DEFAULT_SELECTOR_METHOD
    )

    # Set dependency file according to priority order
    config.dependency_file = dependency_file or config.dependency_file or None
    return config


def get_logging_level(
    logging_level: AvailableLoggingLevels,
    config_logging_level: Optional[str],
) -> AvailableLoggingLevels:
    """Return the appropriate logging level, considering that the one in config has less priority than the one passed directly."""
    if logging_level is AvailableLoggingLevels.none:
        if config_logging_level:
            return AvailableLoggingLevels[config_logging_level.lower()]
        else:
            # default logging level
            return AvailableLoggingLevels.warning

    return logging_level


def set_logging_level(logging_level: AvailableLoggingLevels) -> None:
    logger.setLevel(logging_level.value)
    logger.debug(f"Logging level: {logging_level.value}")


def get_candidate_selector(selector_method_name: Optional[str]) -> AbstractSelector:
    logger.debug(f"Selector method received {selector_method_name}")
    selector_method_name = selector_method_name or DEFAULT_SELECTOR_METHOD
    selector_method = SELECTOR_METHOD_MAPPING[selector_method_name]()
    logger.debug(f"Instantiated {selector_method} selector")
    return selector_method


def get_parsed_dependencies(dependency_file: Optional[str] = None) -> set[str]:
    dependency_parser = DependencySelector(dependency_file).get_dependency_parser()
    dependencies = dependency_parser.parse()
    logger.debug("Successfully parsed local dependencies file.")
    return dependencies


def normalize_packages(packages: set[str]) -> set[str]:
    """Normalize dependency names according to PyPi https://packaging.python.org/en/latest/specifications/name-normalization/."""
    return {re.sub(r"[-_.]+", "-", name).lower() for name in packages}
