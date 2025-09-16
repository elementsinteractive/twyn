import logging
from collections.abc import Iterable
from typing import Optional, Union

from twyn.base.constants import (
    MANUAL_INPUT_SOURCE,
    SELECTOR_METHOD_MAPPING,
    PackageEcosystems,
    SelectorMethod,
)
from twyn.config.config_handler import ConfigHandler, TwynConfiguration
from twyn.config.exceptions import InvalidSelectorMethodError
from twyn.dependency_managers.managers.base import BaseDependencyManager
from twyn.dependency_managers.utils import (
    PACKAGE_ECOSYSTEMS,
    get_dependency_manager_from_file,
    get_dependency_manager_from_name,
)
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.file_handler.file_handler import FileHandler
from twyn.similarity.algorithm import EditDistance, SimilarityThreshold
from twyn.trusted_packages.cache_handler import CacheHandler
from twyn.trusted_packages.exceptions import InvalidArgumentsError
from twyn.trusted_packages.models import (
    TyposquatCheckResultEntry,
    TyposquatCheckResultFromSource,
    TyposquatCheckResults,
)
from twyn.trusted_packages.references.base import AbstractPackageReference
from twyn.trusted_packages.trusted_packages import TrustedPackages

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
) -> TyposquatCheckResults:
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
    maybe_cache_handler = CacheHandler() if config.use_cache else None
    selector_method_obj = _get_selector_method(config.selector_method)

    if dependencies:  # Dependencies where input manually, will not read dependency files.
        return _analyze_dependencies_from_input(
            selector_method=selector_method_obj,
            source=config.source,
            maybe_cache_handler=maybe_cache_handler,
            allowlist=config.allowlist,
            show_progress_bar=show_progress_bar,
            package_ecosystem=config.package_ecosystem,
            dependencies=dependencies,
        )

    if config.package_ecosystem:
        logger.warning("`package_ecosystem` is not supported when reading dependencies from files. It will be ignored.")

    return _analyze_packages_from_source(
        selector_method=selector_method_obj,
        source=config.source,
        maybe_cache_handler=maybe_cache_handler,
        allowlist=config.allowlist,
        show_progress_bar=show_progress_bar,
        dependency_file=config.dependency_file,
    )


def _analyze_dependencies_from_input(
    package_ecosystem: Optional[PackageEcosystems],
    selector_method: SelectorMethod,
    source: Optional[str],
    maybe_cache_handler: Optional[CacheHandler],
    dependencies: set[str],
    allowlist: set[str],
    show_progress_bar: bool,
) -> TyposquatCheckResults:
    """Analyze dependencies when they are passed as an argument to the main method.

    All dependencies analyzed like this will have as source `manual_input`.
    """
    if not package_ecosystem:
        raise InvalidArgumentsError("`package_ecosystem` is required when using `dependencies`.")
    if package_ecosystem not in PACKAGE_ECOSYSTEMS:
        raise InvalidArgumentsError("Not a valid `package_ecosystem`.")

    dependency_manager = get_dependency_manager_from_name(package_ecosystem)
    top_package_reference = dependency_manager.trusted_packages_source(source, maybe_cache_handler)
    trusted_packages = TrustedPackages(
        names=top_package_reference.get_packages(),
        algorithm=EditDistance(),
        selector=selector_method,
        threshold_class=SimilarityThreshold,
    )
    possible_typos = _analyze_dependencies(
        top_package_reference, trusted_packages, dependencies, allowlist, show_progress_bar
    )
    if possible_typos:
        return TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=possible_typos,
                    source=MANUAL_INPUT_SOURCE,
                )
            ]
        )
    return TyposquatCheckResults()


def _analyze_packages_from_source(
    allowlist: set[str],
    selector_method: SelectorMethod,
    show_progress_bar: bool,
    dependency_file: Optional[str],
    source: Optional[str],
    maybe_cache_handler: Optional[CacheHandler],
) -> TyposquatCheckResults:
    """Analyze dependencies from a dependencies file.

    It will return a list of the possible typos grouped by source, each source being a dependency file.
    """
    dependency_managers = _get_dependency_managers_and_parsers_mapping(dependency_file)
    typos_by_file = TyposquatCheckResults()
    for dependency_manager, parsers in dependency_managers.items():
        top_package_reference = dependency_manager.trusted_packages_source(source, maybe_cache_handler)
        packages_from_source = top_package_reference.get_packages()
        trusted_packages = TrustedPackages(
            names=packages_from_source,
            algorithm=EditDistance(),
            selector=selector_method,
            threshold_class=SimilarityThreshold,
        )
        results: list[TyposquatCheckResultFromSource] = []
        for parser in parsers:
            analyzed_dependencies = _analyze_dependencies(
                top_package_reference, trusted_packages, parser.parse(), allowlist, show_progress_bar
            )

            if analyzed_dependencies:
                results.append(
                    TyposquatCheckResultFromSource(source=str(parser.file_path), errors=analyzed_dependencies)
                )
        typos_by_file.results += results

    return typos_by_file


def _analyze_dependencies(
    top_package_reference: AbstractPackageReference,
    trusted_packages: TrustedPackages,
    packages: set[str],
    allowlist: set[str],
    show_progress_bar: bool,
) -> list[TyposquatCheckResultEntry]:
    """Analyze the set of given dependencies against the trusted packages' golden set.

    Each possible typo is returned in a `TyposquatCheckResultEntry`. A list of possible typos will be returned.
    """
    normalized_allowlist_packages = top_package_reference.normalize_packages(allowlist)
    normalized_dependencies = top_package_reference.normalize_packages(packages)

    errors = []

    for dependency in _get_dependencies_list(normalized_dependencies, show_progress_bar):
        if dependency in normalized_allowlist_packages:
            logger.info("Dependency %s is in the allowlist", dependency)
            continue

        logger.info("Analyzing %s", dependency)
        if dependency not in trusted_packages and (typosquat_results := trusted_packages.get_typosquat(dependency)):
            errors.append(typosquat_results)

    return errors


def _get_dependencies_list(normalized_dependencies: set[str], show_progress_bar: bool) -> Iterable[str]:
    """Determine if the progress bar will be showed or not. It returns an iterable of all the dependencies to analyze."""
    try:
        from rich.progress import track  # noqa: PLC0415

        return (
            track(normalized_dependencies, description="Processing...")
            if show_progress_bar
            else normalized_dependencies
        )
    except ImportError as e:
        if show_progress_bar:
            raise InvalidArgumentsError(
                "Cannot show progress bar because `rich` dependency is not installed. "
                "It is only meant to be shown when running `twyn` as a cli tool. "
                "If this is you case, install all the dependencies with `pip install twyn[cli]`. "
            ) from e
        return normalized_dependencies


def _get_selector_method(selector_method: str) -> SelectorMethod:
    """Return the selector_method from set of available ones."""
    if selector_method not in SELECTOR_METHOD_MAPPING:
        InvalidSelectorMethodError("Invalid selector method")

    return SELECTOR_METHOD_MAPPING[selector_method]()


def _get_dependency_managers_and_parsers_mapping(
    dependency_file: Optional[str],
) -> dict[type[BaseDependencyManager], list[AbstractParser]]:
    """Return a dictionary, grouping all files to parse by their DependencyManager."""
    dependency_managers: dict[type[BaseDependencyManager], list[AbstractParser]] = {}

    # No dependencies introduced via the CLI, so the dependecy file was either given or will be auto-detected
    dependency_selector = DependencySelector(dependency_file)
    dependency_parsers = dependency_selector.get_dependency_parsers()

    for parser in dependency_parsers:
        manager = get_dependency_manager_from_file(parser.file_path)

        if manager not in dependency_managers:
            dependency_managers[manager] = []
        dependency_managers[manager].append(parser)
    return dependency_managers


def _get_config(
    load_config_from_file: bool,
    config_file: Optional[str],
    selector_method: Union[SelectorMethod, None],
    dependency_file: Optional[str],
    use_cache: Optional[bool],
    package_ecosystem: Optional[PackageEcosystems],
) -> TwynConfiguration:
    """Given the arguments passed to the main function and the configuration loaded from the config file (if any), return a config object."""
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
