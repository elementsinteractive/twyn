import logging
from collections.abc import Iterable

from twyn.base.constants import (
    MANUAL_INPUT_SOURCE,
    SELECTOR_METHOD_MAPPING,
    PackageEcosystems,
    SelectorMethod,
)
from twyn.config.config_handler import ConfigHandler, TwynConfiguration
from twyn.config.exceptions import InvalidSelectorMethodError
from twyn.dependency_managers.managers import (
    PACKAGE_ECOSYSTEMS,
    get_dependency_manager_from_file,
    get_dependency_manager_from_name,
)
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.exceptions import InvalidFileFormatError
from twyn.file_handler.exceptions import EmptyFileError
from twyn.file_handler.file_handler import FileHandler
from twyn.similarity.algorithm import EditDistance, SimilarityThreshold
from twyn.trusted_packages.cache_handler import CacheHandler
from twyn.trusted_packages.exceptions import InvalidArgumentsError
from twyn.trusted_packages.managers.base import TrustedPackagesProtocol
from twyn.trusted_packages.models import (
    TyposquatCheckResultEntry,
    TyposquatCheckResultFromSource,
    TyposquatCheckResults,
)
from twyn.trusted_packages.references.base import AbstractPackageReference

logger = logging.getLogger("twyn")
logger.addHandler(logging.NullHandler())


def check_dependencies(
    selector_method: SelectorMethod | None = None,
    config_file: str | None = None,
    dependency_files: set[str] | None = None,
    dependencies: set[str] | None = None,
    use_cache: bool | None = True,
    show_progress_bar: bool = False,
    load_config_from_file: bool = False,
    package_ecosystem: PackageEcosystems | None = None,
    recursive: bool | None = None,
    pypi_source: str | None = None,
    npm_source: str | None = None,
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
        dependency_files=dependency_files,
        use_cache=use_cache,
        package_ecosystem=package_ecosystem,
        recursive=recursive,
        pypi_source=pypi_source,
        npm_source=npm_source,
    )
    maybe_cache_handler = CacheHandler() if config.use_cache else None
    selector_method_obj = _get_selector_method(config.selector_method)

    if dependencies:  # Dependencies where input manually, will not read dependency files.
        return _analyze_dependencies_from_input(
            selector_method=selector_method_obj,
            pypi_source=config.pypi_source,
            npm_source=config.npm_source,
            maybe_cache_handler=maybe_cache_handler,
            allowlist=config.allowlist,
            show_progress_bar=show_progress_bar,
            package_ecosystem=config.package_ecosystem,
            dependencies=dependencies,
        )

    # The following checks do not result in an error to avoid inconsistencies.
    # If the user has set in the config file a setting that would conflict with a cli provided option
    # it would always result in an execution error rather than in overriding the behaviour.
    if config.package_ecosystem:
        logger.warning("`package_ecosystem` is not supported when reading dependencies from files. It will be ignored.")

    if config.dependency_files and config.recursive:
        logger.warning(
            "`--recursive` has been set together with `--dependency-file`. `--dependency-file` will take precedence."
        )

    return _analyze_dependencies_from_source(
        selector_method=selector_method_obj,
        pypi_source=config.pypi_source,
        npm_source=config.npm_source,
        maybe_cache_handler=maybe_cache_handler,
        allowlist=config.allowlist,
        show_progress_bar=show_progress_bar,
        dependency_files=config.dependency_files,
    )


def _analyze_dependencies_from_input(
    package_ecosystem: PackageEcosystems | None,
    selector_method: SelectorMethod,
    pypi_source: str | None,
    npm_source: str | None,
    maybe_cache_handler: CacheHandler | None,
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
    source = dependency_manager.get_alternative_source({"pypi": pypi_source, "npm": npm_source})
    top_package_reference = dependency_manager.trusted_packages_source(source, maybe_cache_handler)
    trusted_packages = dependency_manager.trusted_packages_manager(
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


def _analyze_dependencies_from_source(
    allowlist: set[str],
    selector_method: SelectorMethod,
    show_progress_bar: bool,
    dependency_files: set[str] | None,
    pypi_source: str | None,
    npm_source: str | None,
    maybe_cache_handler: CacheHandler | None,
) -> TyposquatCheckResults:
    """Analyze dependencies from a dependencies file.

    It will return a list of the possible typos grouped by source, each source being a dependency file.
    """
    typos_by_file = TyposquatCheckResults()

    dependency_managers = _get_dependency_managers_and_parsers_mapping(dependency_files)
    for ecosystem_name, parsers in dependency_managers.items():
        manager = get_dependency_manager_from_name(ecosystem_name)
        source = manager.get_alternative_source({"pypi": pypi_source, "npm": npm_source})
        top_package_reference = manager.trusted_packages_source(source, maybe_cache_handler)

        packages_from_source = top_package_reference.get_packages()
        trusted_packages = manager.trusted_packages_manager(
            names=packages_from_source,
            algorithm=EditDistance(),
            selector=selector_method,
            threshold_class=SimilarityThreshold,
        )
        results: list[TyposquatCheckResultFromSource] = []
        for parser in parsers:
            try:
                parsed_content = parser.parse()
            except (InvalidFileFormatError, EmptyFileError) as e:
                logger.warning("Could not parse %s. %s", parser.file_path, e)
                continue

            if not parsed_content:
                logger.warning("No packages found in %s. Skipping...", parser.file_path)
                continue

            analyzed_dependencies = _analyze_dependencies(
                top_package_reference,
                trusted_packages,
                parsed_content,
                allowlist,
                show_progress_bar,
                parser.file_path,
            )

            if analyzed_dependencies:
                results.append(
                    TyposquatCheckResultFromSource(source=str(parser.file_path), errors=analyzed_dependencies)
                )
        typos_by_file.results += results

    return typos_by_file


def _analyze_dependencies(
    top_package_reference: AbstractPackageReference,
    trusted_packages: TrustedPackagesProtocol,
    packages: set[str],
    allowlist: set[str],
    show_progress_bar: bool,
    dependency_file: str | None = None,
) -> list[TyposquatCheckResultEntry]:
    """Analyze the set of given dependencies against the trusted packages' golden set.

    Each possible typo is returned in a `TyposquatCheckResultEntry`. A list of possible typos will be returned.
    """
    normalized_allowlist_packages = top_package_reference.normalize_packages(allowlist)
    normalized_dependencies = top_package_reference.normalize_packages(packages)

    errors = []
    for dependency in _get_dependencies_list(normalized_dependencies, show_progress_bar, dependency_file):
        if dependency in normalized_allowlist_packages:
            logger.info("Dependency %s is in the allowlist", dependency)
            continue

        logger.info("Analyzing %s", dependency)
        if dependency not in trusted_packages and (typosquat_results := trusted_packages.get_typosquat(dependency)):
            errors.append(typosquat_results)

    return errors


def _get_dependencies_list(
    normalized_dependencies: set[str], show_progress_bar: bool, dependency_file: str | None = None
) -> Iterable[str]:
    """Return an iterable of dependencies, optionally with progress tracking."""
    if not show_progress_bar:
        return normalized_dependencies

    try:
        from rich.progress import track  # noqa: PLC0415

        if dependency_file:
            from click import echo, style  # noqa: PLC0415

            echo(style(f"Reading file {dependency_file}", fg="green"), color=True)

        return track(normalized_dependencies, description="Processing...")

    except ModuleNotFoundError as e:
        raise InvalidArgumentsError(
            "Cannot show progress bar because `rich` and `click` dependencies are not installed. "
            "It is only meant to be shown when running `twyn` as a cli tool. "
            "If this is you case, install all the dependencies with `pip install twyn[cli]`. "
        ) from e


def _get_selector_method(selector_method: str) -> SelectorMethod:
    """Return the selector_method from set of available ones."""
    if selector_method not in SELECTOR_METHOD_MAPPING:
        InvalidSelectorMethodError("Invalid selector method")

    return SELECTOR_METHOD_MAPPING[selector_method]()


def _get_dependency_managers_and_parsers_mapping(
    dependency_files: set[str] | None,
) -> dict[str, list[AbstractParser]]:
    """Return a dictionary, grouping all files to parse by their DependencyManager."""
    dependency_managers: dict[str, list[AbstractParser]] = {}

    # No dependencies introduced via the CLI, so the dependecy file was either given or will be auto-detected
    dependency_selector = DependencySelector(dependency_files)
    dependency_parsers = dependency_selector.get_dependency_parsers()

    for parser in dependency_parsers:
        manager = get_dependency_manager_from_file(parser.file_path)

        if manager.name not in dependency_managers:
            dependency_managers[manager.name] = []
        dependency_managers[manager.name].append(parser)
    return dependency_managers


def _get_config(
    load_config_from_file: bool,
    config_file: str | None,
    selector_method: SelectorMethod | None,
    dependency_files: set[str] | None,
    use_cache: bool | None,
    package_ecosystem: PackageEcosystems | None,
    recursive: bool | None,
    pypi_source: str | None,
    npm_source: str | None,
) -> TwynConfiguration:
    """Given the arguments passed to the main function and the configuration loaded from the config file (if any), return a config object."""
    if load_config_from_file:
        config_file_handler = FileHandler(config_file or ConfigHandler.get_default_config_file_path())
    else:
        config_file_handler = None
    return ConfigHandler(config_file_handler).resolve_config(
        selector_method=selector_method,
        dependency_files=dependency_files,
        use_cache=use_cache,
        package_ecosystem=package_ecosystem,
        recursive=recursive,
        pypi_source=pypi_source,
        npm_source=npm_source,
    )
