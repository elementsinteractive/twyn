import logging
from typing import Optional, Union

from rich.progress import track

from twyn.base.constants import (
    SELECTOR_METHOD_MAPPING,
    PackageEcosystems,
    SelectorMethod,
)
from twyn.config.config_handler import ConfigHandler, TwynConfiguration
from twyn.config.exceptions import InvalidSelectorMethodError
from twyn.dependency_managers.dependency_manager import (
    PACKAGE_ECOSYSTEMS,
    get_dependency_manager_from_file,
    get_dependency_manager_from_name,
)
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.file_handler.file_handler import FileHandler
from twyn.similarity.algorithm import EditDistance, SimilarityThreshold
from twyn.trusted_packages.cache_handler import CacheHandler
from twyn.trusted_packages.exceptions import InvalidArgumentsError
from twyn.trusted_packages.references import AbstractPackageReference
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
    package_ecosystem: Optional[PackageEcosystems] = None,
) -> TyposquatCheckResultList:
    """
    Check if the provided dependencies are potential typosquats of trusted packages.

    This function analyzes a set of dependencies and determines if any of them are likely typosquats
    (i.e., malicious or mistaken variants) of popular or trusted packages, using configurable methods
    and references.

    Args:
        selector_method: The method used to select candidate typosquat matches.
        config_file: Path to a configuration file to load settings from.
        dependency_file: Path to a file containing the list of dependencies to check.
        dependencies: A set of dependency names to check. If not provided, dependencies are loaded from the dependency_file.
        use_cache: Whether to use cached data for package references and results. Defaults to True.
        show_progress_bar: Whether to display a progress bar during processing. Defaults to False.
        load_config_from_file: Whether to load configuration from the specified config_file. Defaults to False.
        package_ecosystems: The package ecosystem to use
    Returns:
        TyposquatCheckResultList: A list of results indicating which dependencies, if any, are suspected typosquats.
    """
    config = _get_config(
        load_config_from_file=load_config_from_file,
        config_file=config_file,
        selector_method=selector_method,
        dependency_file=dependency_file,
        use_cache=use_cache,
        package_ecosystem=package_ecosystem,
    )

    selector_method = _get_selector_method(config.selector_method)

    dependencies_to_check, top_package_reference = _get_dependencies_to_check_and_top_package_reference(
        config.package_ecosystem,
        dependencies,
        config.source,
        config.dependency_file,
        config.use_cache,
    )

    trusted_packages = TrustedPackages(
        names=top_package_reference.get_packages(),
        algorithm=EditDistance(),
        selector=selector_method,
        threshold_class=SimilarityThreshold,
    )
    normalized_allowlist_packages = top_package_reference.normalize_packages(config.allowlist)
    normalized_dependencies = top_package_reference.normalize_packages(dependencies_to_check)

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


def _get_selector_method(selector_method: str) -> SelectorMethod:
    if selector_method not in SELECTOR_METHOD_MAPPING:
        InvalidSelectorMethodError("Invalid selector method")

    return SELECTOR_METHOD_MAPPING[selector_method]()


def _get_dependencies_to_check_and_top_package_reference(
    package_ecosystem: str,
    dependencies: Optional[set[str]],
    source: str,
    dependency_file: Optional[str],
    use_cache: bool,
) -> tuple[Optional[set[str]], AbstractPackageReference]:
    dependency_selector: Optional[DependencySelector] = None
    cache_handler = CacheHandler() if use_cache else None

    if dependencies:
        if not package_ecosystem:
            raise InvalidArgumentsError("`package_ecosystem` is required when using `dependencies`.")
        if package_ecosystem not in PACKAGE_ECOSYSTEMS:
            raise InvalidArgumentsError("not a valid programming language")

        dependencies_to_check = dependencies
        dependency_manager = get_dependency_manager_from_name(package_ecosystem)
        return dependencies_to_check, dependency_manager.trusted_packages_source(source, cache_handler)

    # No dependencies introduced via the CLI, so the dependecy file was either given or will be auto-detected
    dependency_selector = DependencySelector(dependency_file)
    dependency_parser = dependency_selector.get_dependency_parser()
    dependency_manager = get_dependency_manager_from_file(dependency_selector.dependency_file)

    if package_ecosystem and dependency_manager.name != package_ecosystem:
        raise InvalidArgumentsError("Given `package_ecosystem` does not match `dependency_file`'s `package_ecosystem`")

    dependencies_to_check = dependency_parser.parse()
    return dependencies_to_check, dependency_manager.trusted_packages_source(source, cache_handler)


def _get_config(
    load_config_from_file: bool,
    config_file: Optional[str],
    selector_method: Union[SelectorMethod, None],
    dependency_file: Optional[str],
    use_cache: Optional[bool],
    package_ecosystem: Optional[PackageEcosystems],
) -> TwynConfiguration:
    if load_config_from_file:
        config_file_handler = FileHandler(config_file or ConfigHandler.get_default_config_file_path())
    else:
        config_file_handler = None
    return ConfigHandler(config_file_handler).resolve_config(
        selector_method=selector_method,
        dependency_file=dependency_file,
        use_cache=use_cache,
        package_ecosystem=package_ecosystem,
    )
