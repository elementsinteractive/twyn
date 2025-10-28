import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from tomlkit import TOMLDocument, dumps, load, table

from twyn.base.constants import (
    DEFAULT_PROJECT_TOML_FILE,
    DEFAULT_RECURSIVE,
    DEFAULT_SELECTOR_METHOD,
    DEFAULT_TWYN_TOML_FILE,
    DEFAULT_USE_CACHE,
    SELECTOR_METHOD_KEYS,
    PackageEcosystems,
)
from twyn.config.exceptions import (
    AllowlistPackageAlreadyExistsError,
    AllowlistPackageDoesNotExistError,
    ConfigFileNotConfiguredError,
    InvalidSelectorMethodError,
    TOMLError,
)
from twyn.file_handler.exceptions import PathNotFoundError
from twyn.file_handler.file_handler import FileHandler

logger = logging.getLogger("twyn")


@dataclass(frozen=True)
class TwynConfiguration:
    """Fully resolved configuration for Twyn."""

    dependency_files: set[str]
    """Set of dependency file paths to analyze."""
    selector_method: str
    """Method for selecting similar packages."""
    allowlist: set[str]
    """Set of package names to allow without checking."""
    pypi_source: str | None
    """Alternative PyPI source URL."""
    npm_source: str | None
    """Alternative npm source URL."""
    use_cache: bool
    """Whether to use cached trusted packages."""
    package_ecosystem: PackageEcosystems | None
    """Target package ecosystem for analysis."""
    recursive: bool | None
    """Whether to recursively search for dependency files."""


@dataclass
class ReadTwynConfiguration:
    """Configuration for twyn as set by the user. It may have None values."""

    dependency_files: set[str] | None = field(default_factory=set)
    """Optional set of dependency file paths to analyze."""
    selector_method: str | None = None
    """Optional method for selecting similar packages."""
    allowlist: set[str] = field(default_factory=set)
    """Set of package names to allow without checking."""
    pypi_source: str | None = None
    """Optional alternative PyPI source URL."""
    npm_source: str | None = None
    """Optional alternative npm source URL."""
    use_cache: bool | None = None
    """Optional setting for using cached trusted packages."""
    package_ecosystem: PackageEcosystems | None = None
    """Optional target package ecosystem for analysis."""
    recursive: bool | None = None
    """Optional setting for recursive dependency file search."""


class ConfigHandler:
    """Manage reading and writing configurations for Twyn."""

    def __init__(self, file_handler: FileHandler | None = None) -> None:
        self.file_handler = file_handler

    def resolve_config(  # noqa: C901, PLR0912
        self,
        selector_method: str | None = None,
        dependency_files: set[str] | None = None,
        use_cache: bool | None = None,
        package_ecosystem: PackageEcosystems | None = None,
        recursive: bool | None = None,
        pypi_source: str | None = None,
        npm_source: str | None = None,
    ) -> TwynConfiguration:
        """Resolve the configuration for Twyn.

        Given the cli flags it will return a fully resolved configuration for Twyn,
        giving precedence to cli flags vs values set in the config files.

        It will also handle default values, when appropriate.
        """
        if self.file_handler:
            toml = self._read_toml()
            read_config = self._get_read_config(toml)
        else:
            # When we're running twyn as a package we may not be interested on loading the config from the config file.
            read_config = ReadTwynConfiguration()

        # Determine final selector method from CLI, config file, or default
        final_selector_method = selector_method or read_config.selector_method or DEFAULT_SELECTOR_METHOD

        # Validate selector_method
        if final_selector_method not in SELECTOR_METHOD_KEYS:
            valid_methods = ", ".join(sorted(SELECTOR_METHOD_KEYS))
            raise InvalidSelectorMethodError(
                f"Invalid selector_method '{final_selector_method}'. Must be one of: {valid_methods}"
            )
        if use_cache is not None:
            final_use_cache = use_cache
        elif read_config.use_cache is not None:
            final_use_cache = read_config.use_cache
        else:
            final_use_cache = DEFAULT_USE_CACHE

        if recursive is not None:
            final_recursive = recursive
        elif read_config.recursive is not None:
            final_recursive = read_config.recursive
        else:
            final_recursive = DEFAULT_RECURSIVE

        # Determine final pypi_source from CLI, config file, or default
        if pypi_source is not None:
            final_pypi_source = pypi_source
        elif read_config.pypi_source is not None:
            final_pypi_source = read_config.pypi_source
        else:
            final_pypi_source = None

        # Determine final npm_source from CLI, config file, or default
        if npm_source is not None:
            final_npm_source = npm_source
        elif read_config.npm_source is not None:
            final_npm_source = read_config.npm_source
        else:
            final_npm_source = None

        return TwynConfiguration(
            dependency_files=dependency_files or read_config.dependency_files or set(),
            selector_method=final_selector_method,
            allowlist=read_config.allowlist,
            pypi_source=final_pypi_source,
            npm_source=final_npm_source,
            use_cache=final_use_cache,
            package_ecosystem=package_ecosystem or read_config.package_ecosystem,
            recursive=final_recursive,
        )

    def add_package_to_allowlist(self, package_name: str) -> None:
        """Add a package to the allowlist configuration in the toml file."""
        toml = self._read_toml()
        config = self._get_read_config(toml)
        if package_name in config.allowlist:
            raise AllowlistPackageAlreadyExistsError(package_name)

        config.allowlist.add(package_name)
        self._write_config(toml, config)
        logger.info("Package '%s' successfully added to allowlist", package_name)

    def remove_package_from_allowlist(self, package_name: str) -> None:
        """Remove a package from the allowlist configuration in the toml file."""
        toml = self._read_toml()
        config = self._get_read_config(toml)
        if package_name not in config.allowlist:
            raise AllowlistPackageDoesNotExistError(package_name)

        config.allowlist.remove(package_name)
        self._write_config(toml, config)
        logger.info("Package '%s' successfully removed from allowlist", package_name)

    def _get_read_config(self, toml: TOMLDocument) -> ReadTwynConfiguration:
        """Read the twyn configuration from a provided toml document."""
        twyn_config_data = toml.get("tool", {}).get("twyn", {})

        dependency_file = twyn_config_data.get("dependency_file", set())
        if isinstance(dependency_file, str):
            dependency_file = {dependency_file}
        elif isinstance(dependency_file, list):
            dependency_file = set(dependency_file)

        allowlist = twyn_config_data.get("allowlist", set())
        if isinstance(allowlist, str):
            allowlist = {allowlist}
        elif isinstance(allowlist, list):
            allowlist = set(allowlist)

        return ReadTwynConfiguration(
            dependency_files=dependency_file,
            selector_method=twyn_config_data.get("selector_method"),
            allowlist=allowlist,
            pypi_source=twyn_config_data.get("pypi_source"),
            npm_source=twyn_config_data.get("npm_source"),
            use_cache=twyn_config_data.get("use_cache"),
            package_ecosystem=twyn_config_data.get("package_ecosystem"),
            recursive=twyn_config_data.get("recursive"),
        )

    def _write_config(self, toml: TOMLDocument, config: ReadTwynConfiguration) -> None:
        """Write the configuration to the toml file.

        All null values are simply omitted from the toml file.
        """
        twyn_toml_data = asdict(config, dict_factory=lambda x: _serialize_config(x))

        if "tool" not in toml:
            toml.add("tool", table())
        if "twyn" not in toml["tool"]:  # type: ignore[operator]
            toml["tool"]["twyn"] = {}  # type: ignore[index]
        toml["tool"]["twyn"] = twyn_toml_data  # type: ignore[index]
        self._write_toml(toml)

    def _write_toml(self, toml: TOMLDocument) -> None:
        """Write TOML document to file."""
        if not self.file_handler:
            raise ConfigFileNotConfiguredError("Config file not configured. Cannot perform write operation.")
        self.file_handler.write(dumps(toml))

    def _read_toml(self) -> TOMLDocument:
        """Read TOML document from file."""
        if not self.file_handler:
            raise ConfigFileNotConfiguredError("Config file not configured. Cannot perform read operation.")
        try:
            with self.file_handler.open("rb") as fp:
                return load(fp)
        except PathNotFoundError:
            if self.file_handler.is_handler_of_file(DEFAULT_PROJECT_TOML_FILE):
                return TOMLDocument()
            raise TOMLError(f"Error reading toml from {self.file_handler.file_path}") from None

    @staticmethod
    def get_default_config_file_path() -> str:
        """Return `twyn.toml` if it exists. If not, it returns the default `pyproject.toml` file.

        It does not fail if the latter does not exist, as it is not mandatory to have a config file to run twyn.
        """
        if Path(DEFAULT_TWYN_TOML_FILE).exists():
            return DEFAULT_TWYN_TOML_FILE
        return DEFAULT_PROJECT_TOML_FILE


def _serialize_config(x: Any) -> Any | str | list[Any]:
    """Serialize configuration values for TOML format."""

    def _value_to_for_config(v: Any) -> str | list[Any] | Any:
        if isinstance(v, Enum):
            return v.name
        elif isinstance(v, set):
            return list(v)
        return v

    return {k: _value_to_for_config(v) for (k, v) in x if v is not None and v != set()}
