import logging
from typing import Optional, Union

from rich.progress import track

from twyn.base.constants import (
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
    TyposquatCheckResultList,
)

logger = logging.getLogger("twyn")


def check_dependencies(
    selector_method: Union[SelectorMethod, None] = None,
    config_file: Optional[str] = None,
    dependency_file: Optional[str] = None,
    dependencies: Optional[set[str]] = None,
    verbosity: AvailableLoggingLevels = AvailableLoggingLevels.none,
    use_cache: Optional[bool] = True,
    use_track: bool = False,
    load_config_from_file: bool = False,
) -> TyposquatCheckResultList:
    """Check if dependencies could be typosquats."""
    config = get_config(
        load_config_from_file=load_config_from_file,
        config_file=config_file,
        verbosity=verbosity,
        selector_method=selector_method,
        dependency_file=dependency_file,
        use_cache=use_cache,
    )

    _set_logging_level(config.logging_level)

    cache_handler = CacheHandler() if config.use_cache else None

    trusted_packages = TrustedPackages(
        names=TopPyPiReference(source=config.pypi_reference, cache_handler=cache_handler).get_packages(),
        algorithm=EditDistance(),
        selector=get_candidate_selector(config.selector_method),
        threshold_class=SimilarityThreshold,
    )
    normalized_allowlist_packages = normalize_packages(config.allowlist)
    dependencies = dependencies if dependencies else get_parsed_dependencies_from_file(config.dependency_file)
    normalized_dependencies = normalize_packages(dependencies)

    typos_list = TyposquatCheckResultList()
    dependencies_list = (
        track(normalized_dependencies, description="Processing...") if use_track else normalized_dependencies
    )
    for dependency in dependencies_list:
        if dependency in normalized_allowlist_packages:
            logger.info("Dependency %s is in the allowlist", dependency)
            continue

        logger.info("Analyzing %s", dependency)
        if dependency not in trusted_packages and (typosquat_results := trusted_packages.get_typosquat(dependency)):
            typos_list.errors.append(typosquat_results)

    return typos_list


def get_config(
    load_config_from_file: bool,
    config_file: Optional[str],
    verbosity: AvailableLoggingLevels,
    selector_method: Union[SelectorMethod, None],
    dependency_file: Optional[str],
    use_cache: Optional[bool],
) -> ConfigHandler:
    if load_config_from_file:
        config_file_handler = FileHandler(config_file or ConfigHandler.get_default_config_file_path())
    else:
        config_file_handler = None
    return ConfigHandler(config_file_handler).resolve_config(
        verbosity=verbosity,
        selector_method=selector_method,
        dependency_file=dependency_file,
        use_cache=use_cache,
    )


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
