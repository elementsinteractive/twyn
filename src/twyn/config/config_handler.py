import logging
from dataclasses import asdict, dataclass
from enum import Enum
from os import getcwd
from pathlib import Path
from typing import Optional

from tomlkit import TOMLDocument, dumps, parse, table

from twyn.base.constants import (
    DEFAULT_PROJECT_TOML_FILE,
    DEFAULT_SELECTOR_METHOD,
    DEFAULT_TOP_PYPI_PACKAGES,
    AvailableLoggingLevels,
)
from twyn.config.exceptions import (
    AllowlistPackageAlreadyExistsError,
    AllowlistPackageDoesNotExistError,
    TOMLError,
)

logger = logging.getLogger("twyn")


@dataclass(frozen=True)
class TwynConfiguration:
    """Fully resolved configuration for Twyn."""

    dependency_file: Optional[str]
    selector_method: str
    logging_level: AvailableLoggingLevels
    allowlist: set[str]
    pypi_reference: str


@dataclass
class ReadTwynConfiguration:
    """Configuration for twyn as set by the user. It may have None values."""

    dependency_file: Optional[str]
    selector_method: Optional[str]
    logging_level: Optional[AvailableLoggingLevels]
    allowlist: set[str]
    pypi_reference: Optional[str]


class ConfigHandler:
    """Manage reading and writing configurations for Twyn."""

    def __init__(self, file_path: Optional[str] = None, enforce_file: bool = True):
        self._file_path = file_path or DEFAULT_PROJECT_TOML_FILE
        self._enforce_file = enforce_file

    def resolve_config(
        self,
        selector_method: Optional[str] = None,
        dependency_file: Optional[str] = None,
        verbosity: AvailableLoggingLevels = AvailableLoggingLevels.none,
    ) -> TwynConfiguration:
        """Resolve the configuration for Twyn.

        Given the cli flags it will return a fully resolved configuration for Twyn,
        giving precedence to cli flags vs values set in the config files.

        It will also handle default values, when appropriate.
        """
        toml = self._read_toml()
        read_config = self._get_read_config(toml)

        return TwynConfiguration(
            dependency_file=dependency_file or read_config.dependency_file,
            selector_method=selector_method or read_config.selector_method or DEFAULT_SELECTOR_METHOD,
            logging_level=_get_logging_level(verbosity, read_config.logging_level),
            allowlist=read_config.allowlist,
            pypi_reference=read_config.pypi_reference or DEFAULT_TOP_PYPI_PACKAGES,
        )

    def add_package_to_allowlist(self, package_name: str) -> None:
        """Add a package to the allowlist configuration in the toml file."""
        toml = self._read_toml()
        config = self._get_read_config(toml)
        if package_name in config.allowlist:
            raise AllowlistPackageAlreadyExistsError(package_name)

        config.allowlist.add(package_name)
        self._write_config(toml, config)
        logger.info(f"Package '{package_name}' successfully added to allowlist")

    def remove_package_from_allowlist(self, package_name: str) -> None:
        """Remove a package from the allowlist configuration in the toml file."""
        toml = self._read_toml()
        config = self._get_read_config(toml)
        if package_name not in config.allowlist:
            raise AllowlistPackageDoesNotExistError(package_name)

        config.allowlist.remove(package_name)
        self._write_config(toml, config)
        logger.info(f"Package '{package_name}' successfully removed from allowlist")

    def _get_read_config(self, toml: TOMLDocument) -> ReadTwynConfiguration:
        """Read the twyn configuration from a provided toml document."""
        twyn_config_data = toml.get("tool", {}).get("twyn", {})
        return ReadTwynConfiguration(
            dependency_file=twyn_config_data.get("dependency_file"),
            selector_method=twyn_config_data.get("selector_method"),
            logging_level=twyn_config_data.get("logging_level"),
            allowlist=set(twyn_config_data.get("allowlist", set())),
            pypi_reference=twyn_config_data.get("pypi_reference"),
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

    def _read_toml(self) -> TOMLDocument:
        try:
            fp = self._get_toml_file_pointer()
        except FileNotFoundError:
            if not self._enforce_file and self._file_path == DEFAULT_PROJECT_TOML_FILE:
                return TOMLDocument()
            raise TOMLError(f"Error reading toml from {self._file_path}") from None

        with open(fp, "r") as f:
            content = parse(f.read())
        return content

    def _get_toml_file_pointer(self) -> Path:
        """Create a path for the toml file with the format <current working directory>/self.file_path."""
        fp = Path(getcwd()) / Path(self._file_path)

        if not fp.is_file():
            raise FileNotFoundError(f"File not found at path '{fp}'.")

        return fp

    def _write_toml(self, toml: TOMLDocument) -> None:
        with open(self._get_toml_file_pointer(), "w") as f:
            try:
                f.write(dumps(toml))
            except Exception:
                logger.exception("Error writing toml file")
                raise TOMLError(f"Error writing toml to {self._file_path}") from None


def _get_logging_level(
    cli_verbosity: AvailableLoggingLevels,
    config_logging_level: Optional[str],
) -> AvailableLoggingLevels:
    """Return the appropriate logging level, considering that the one in config has less priority than the one passed directly."""
    if cli_verbosity is AvailableLoggingLevels.none:
        if config_logging_level:
            return AvailableLoggingLevels[config_logging_level.lower()]
        else:
            # default logging level
            return AvailableLoggingLevels.warning
    return cli_verbosity


def _serialize_config(x):
    def _value_to_for_config(v):
        if isinstance(v, Enum):
            return v.name
        elif isinstance(v, set):
            return list(v)
        return v

    return {k: _value_to_for_config(v) for (k, v) in x if v is not None and v != set()}
