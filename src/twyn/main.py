import logging
import re
from typing import Optional

from rich.logging import RichHandler
from rich.progress import track

from twyn.base.constants import (
    SELECTOR_METHOD_MAPPING,
    AvailableLoggingLevels,
)
from twyn.config.config_handler import ConfigHandler
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
    dependency_file: Optional[str],
    dependencies_cli: Optional[set[str]],
    selector_method: str,
    verbosity: AvailableLoggingLevels = AvailableLoggingLevels.none,
) -> bool:
    """Check if dependencies could be typosquats."""
    config = ConfigHandler(file_path=config_file, enforce_file=False).resolve_config(
        verbosity=verbosity, selector_method=selector_method, dependency_file=dependency_file
    )
    _set_logging_level(config.logging_level)

    trusted_packages = TrustedPackages(
        names=TopPyPiReference(source=config.pypi_reference).get_packages(),
        algorithm=EditDistance(),
        selector=get_candidate_selector(config.selector_method),
        threshold_class=SimilarityThreshold,
    )
    normalized_allowlist_packages = _normalize_packages(config.allowlist)
    dependencies = dependencies_cli if dependencies_cli else get_parsed_dependencies_from_file(config.dependency_file)
    normalized_dependencies = _normalize_packages(dependencies)

    errors: list[TyposquatCheckResult] = []
    for dependency in track(normalized_dependencies, description="Processing..."):
        if dependency in normalized_allowlist_packages:
            logger.info(f"Dependency {dependency} is in the allowlist")
            continue

        logger.info(f"Analyzing {dependency}")
        if dependency not in trusted_packages and (typosquat_results := trusted_packages.get_typosquat(dependency)):
            errors.append(typosquat_results)

    for possible_typosquats in errors:
        logger.error(
            f"Possible typosquat detected: `{possible_typosquats.candidate_dependency}`, "
            f"did you mean any of [{', '.join(possible_typosquats.similar_dependencies)}]?"
        )

    return bool(errors)


def _set_logging_level(logging_level: AvailableLoggingLevels) -> None:
    logger.setLevel(logging_level.value)
    logger.debug(f"Logging level: {logging_level.value}")


def get_candidate_selector(selector_method_name: str) -> AbstractSelector:
    logger.debug(f"Selector method received {selector_method_name}")
    selector_method_name = selector_method_name
    selector_method = SELECTOR_METHOD_MAPPING[selector_method_name]()
    logger.debug(f"Instantiated {selector_method} selector")
    return selector_method


def get_parsed_dependencies_from_file(dependency_file: Optional[str] = None) -> set[str]:
    dependency_parser = DependencySelector(dependency_file).get_dependency_parser()
    dependencies = dependency_parser.parse()
    logger.debug("Successfully parsed local dependencies file.")
    return dependencies


def _normalize_packages(packages: set[str]) -> set[str]:
    """Normalize dependency names according to PyPi https://packaging.python.org/en/latest/specifications/name-normalization/."""
    return {re.sub(r"[-_.]+", "-", name).lower() for name in packages}
