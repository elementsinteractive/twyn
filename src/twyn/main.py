import logging
from typing import Optional, Union

from rich.progress import track

from twyn.base.constants import (
    SELECTOR_METHOD_MAPPING,
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
logger.addHandler(logging.NullHandler())


def check_dependencies(
    selector_method: Union[SelectorMethod, None] = None,
    config_file: Optional[str] = None,
    dependency_file: Optional[str] = None,
    dependencies: Optional[set[str]] = None,
    use_cache: Optional[bool] = True,
    show_progress_bar: bool = False,
    load_config_from_file: bool = False,
) -> TyposquatCheckResultList:
    """
    Check if the provided dependencies are potential typosquats of trusted packages.

    This function analyzes a set of dependencies and determines if any of them are likely typosquats
    (i.e., malicious or mistaken variants) of popular or trusted packages, using configurable methods
    and references.

    Args:
        selector_method (Union[SelectorMethod, None], optional): The method used to select candidate typosquat matches.
        config_file (Optional[str], optional): Path to a configuration file to load settings from.
        dependency_file (Optional[str], optional): Path to a file containing the list of dependencies to check.
        dependencies (Optional[set[str]], optional): A set of dependency names to check. If not provided, dependencies are loaded from the dependency_file.
        use_cache (Optional[bool], optional): Whether to use cached data for package references and results. Defaults to True.
        show_progress_bar (bool, optional): Whether to display a progress bar during processing. Defaults to False.
        load_config_from_file (bool, optional): Whether to load configuration from the specified config_file. Defaults to False.

    Returns:
        TyposquatCheckResultList: A list of results indicating which dependencies, if any, are suspected typosquats.
    """
    config = _get_config(
        load_config_from_file=load_config_from_file,
        config_file=config_file,
        selector_method=selector_method,
        dependency_file=dependency_file,
        use_cache=use_cache,
    )

    cache_handler = CacheHandler() if config.use_cache else None

    trusted_packages = TrustedPackages(
        names=TopPyPiReference(source=config.pypi_reference, cache_handler=cache_handler).get_packages(),
        algorithm=EditDistance(),
        selector=_get_candidate_selector(config.selector_method),
        threshold_class=SimilarityThreshold,
    )
    normalized_allowlist_packages = normalize_packages(config.allowlist)
    dependencies = dependencies if dependencies else _get_parsed_dependencies_from_file(config.dependency_file)
    normalized_dependencies = normalize_packages(dependencies)

    typos_list = TyposquatCheckResultList()
    dependencies_list = (
        track(normalized_dependencies, description="Processing...") if show_progress_bar else normalized_dependencies
    )
    for dependency in dependencies_list:
        if dependency in normalized_allowlist_packages:
            logger.info("Dependency %s is in the allowlist", dependency)
            continue

        logger.info("Analyzing %s", dependency)
        if dependency not in trusted_packages and (typosquat_results := trusted_packages.get_typosquat(dependency)):
            typos_list.errors.append(typosquat_results)

    return typos_list


def _get_config(
    load_config_from_file: bool,
    config_file: Optional[str],
    selector_method: Union[SelectorMethod, None],
    dependency_file: Optional[str],
    use_cache: Optional[bool],
) -> ConfigHandler:
    if load_config_from_file:
        config_file_handler = FileHandler(config_file or ConfigHandler.get_default_config_file_path())
    else:
        config_file_handler = None
    return ConfigHandler(config_file_handler).resolve_config(
        selector_method=selector_method,
        dependency_file=dependency_file,
        use_cache=use_cache,
    )


def _get_candidate_selector(selector_method_name: str) -> AbstractSelector:
    logger.debug("Selector method received %s", selector_method_name)
    selector_method = SELECTOR_METHOD_MAPPING[selector_method_name]()
    logger.debug("Instantiated %s selector", selector_method)
    return selector_method


def _get_parsed_dependencies_from_file(dependency_file: Optional[str] = None) -> set[str]:
    dependency_parser = DependencySelector(dependency_file).get_dependency_parser()
    dependencies = dependency_parser.parse()
    logger.debug("Successfully parsed local dependencies file.")
    return dependencies
