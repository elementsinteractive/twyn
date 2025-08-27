import logging
from typing import Optional

from rich.progress import track

from twyn.base.constants import (
    DEFAULT_PROJECT_TOML_FILE,
    SELECTOR_METHOD_MAPPING,
    AvailableLoggingLevels,
    SelectorMethod,
)
from twyn.base.utils import normalize_packages
from twyn.config.config_handler import ConfigHandler
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.file_handler.file_handler import FileHandler
from twyn.similarity.algorithm import EditDistance, SimilarityThreshold
from twyn.trusted_packages import TopPyPiReference
from twyn.trusted_packages.cache_handler import CacheHandler
from twyn.trusted_packages.selectors import AbstractSelector
from twyn.trusted_packages.trusted_packages import (
    TrustedPackages,
    TyposquatCheckResult,
)

logger = logging.getLogger("twyn")


def check_dependencies(
    selector_method: SelectorMethod,
    config_file: Optional[str] = None,
    dependency_file: Optional[str] = None,
    dependencies: Optional[set[str]] = None,
    verbosity: AvailableLoggingLevels = AvailableLoggingLevels.none,
    use_cache: bool = True,
) -> list[TyposquatCheckResult]:
    """Check if dependencies could be typosquats."""
    config_file_handler = FileHandler(config_file or DEFAULT_PROJECT_TOML_FILE)
    config = ConfigHandler(config_file_handler, enforce_file=False).resolve_config(
        verbosity=verbosity, selector_method=selector_method, dependency_file=dependency_file
    )
    _set_logging_level(config.logging_level)

    cache_handler = CacheHandler()
    trusted_packages = TrustedPackages(
        names=TopPyPiReference(source=config.pypi_reference, cache_handler=cache_handler).get_packages(use_cache),
        algorithm=EditDistance(),
        selector=get_candidate_selector(config.selector_method),
        threshold_class=SimilarityThreshold,
    )
    normalized_allowlist_packages = normalize_packages(config.allowlist)
    dependencies = dependencies if dependencies else get_parsed_dependencies_from_file(config.dependency_file)
    normalized_dependencies = normalize_packages(dependencies)

    errors: list[TyposquatCheckResult] = []
    for dependency in track(normalized_dependencies, description="Processing..."):
        if dependency in normalized_allowlist_packages:
            logger.info("Dependency %s is in the allowlist", dependency)
            continue

        logger.info("Analyzing %s", dependency)
        if dependency not in trusted_packages and (typosquat_results := trusted_packages.get_typosquat(dependency)):
            errors.append(typosquat_results)

    return errors


def _set_logging_level(logging_level: AvailableLoggingLevels) -> None:
    logger.setLevel(logging_level.value)
    logger.debug("Logging level: %s", logging_level.value)


def get_candidate_selector(selector_method_name: str) -> AbstractSelector:
    logger.debug("Selector method received %s", selector_method_name)
    selector_method = SELECTOR_METHOD_MAPPING[selector_method_name]()
    logger.debug("Instantiated %s selector", selector_method)
    return selector_method


def get_parsed_dependencies_from_file(dependency_file: Optional[str] = None) -> set[str]:
    dependency_parser = DependencySelector(dependency_file).get_dependency_parser()
    dependencies = dependency_parser.parse()
    logger.debug("Successfully parsed local dependencies file.")
    return dependencies
