import logging
from os import getcwd
from pathlib import Path
from typing import Any, Optional

from tomlkit import dumps, parse

from twyn.base.constants import DEFAULT_PROJECT_TOML_FILE
from twyn.core.exceptions import (
    AllowlistPackageAlreadyExistsError,
    AllowlistPackageDoesNotExistError,
)

logger = logging.getLogger()


class ConfigHandler:
    """Read certain values into a central ConfigHandler object."""

    def __init__(self, file_path: Optional[str] = None, enforce_file: bool = True):
        self._file_path = file_path or DEFAULT_PROJECT_TOML_FILE
        self._enforce_file = enforce_file
        self._toml = self._get_toml_as_dict()
        self._twyn_data = self._get_twyn_data()

        self.dependency_file: Optional[str] = self._twyn_data.get("dependency_file")
        self.selector_method: Optional[str] = self._twyn_data.get("selector_method")
        self.logging_level: Optional[str] = self._twyn_data.get("logging_level")
        self.allowlist: set[str] = set(self._twyn_data.get("allowlist", []))

    def add_package_to_allowlist(self, package_name: str) -> None:
        if package_name in self.allowlist:
            raise AllowlistPackageAlreadyExistsError(package_name)

        self._create_allowlist_in_toml_if_not_exists()

        self._toml["tool"]["twyn"]["allowlist"].append(package_name)
        self._write_toml()

        logger.warning(f"Package '{package_name}' successfully added to allowlist")

    def remove_package_from_allowlist(self, package_name: str) -> None:
        if package_name not in self.allowlist:
            raise AllowlistPackageDoesNotExistError(package_name)

        self._toml["tool"]["twyn"]["allowlist"].remove(package_name)
        self._write_toml()
        logger.warning(f"Package '{package_name}' successfully removed from allowlist")

    def _get_twyn_data(self) -> dict[str, Any]:
        return self._toml.get("tool", {}).get("twyn", {})

    def _get_toml_file_pointer(self) -> Path:
        """Create a path for the toml file with the format <current working directory>/self.file_path."""
        fp = Path(getcwd()) / Path(self._file_path)

        if not fp.is_file():
            raise FileNotFoundError(f"File not found at path '{fp}'.")

        return fp

    def _write_toml(self) -> None:
        with open(self._get_toml_file_pointer(), "w") as f:
            f.write(dumps(self._toml))

    def _get_toml_as_dict(self) -> dict[str, Any]:
        """Read TOML into a dictionary."""
        try:
            fp = self._get_toml_file_pointer()
        except FileNotFoundError:
            if not self._enforce_file and self._file_path == DEFAULT_PROJECT_TOML_FILE:
                return {}
            raise

        with open(fp, "r") as f:
            content = parse(f.read())
        return parse(dumps(content))

    def _create_allowlist_in_toml_if_not_exists(self) -> None:
        try:
            isinstance(self._toml["tool"]["twyn"]["allowlist"], list)
        except KeyError:
            if "tool" not in self._toml:
                self._toml["tool"] = {}

            if "twyn" not in self._toml["tool"]:
                self._toml["tool"]["twyn"] = {}

            if "allowlist" not in self._toml["tool"]["twyn"]:
                self._toml["tool"]["twyn"]["allowlist"] = []
