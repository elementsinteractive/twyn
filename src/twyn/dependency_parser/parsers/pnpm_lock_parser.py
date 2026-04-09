import re
from typing import Any

import yaml
from typing_extensions import override

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import PNPM_LOCK_YAML


class PnpmLockParser(AbstractParser):
    """Parser for pnpm-lock.yaml dependencies."""

    _SCOPED_PACKAGE_PATTERN = re.compile(r"^(@[^@]+/[^@]+)@")
    _REGULAR_PACKAGE_PATTERN = re.compile(r"^([^@]+)@")
    _PACKAGE_NAME_VALIDATION_PATTERN = re.compile(r"^(@[a-zA-Z0-9_.-]+\/)?[a-zA-Z0-9_.-]+$")

    def __init__(self, file_path: str = PNPM_LOCK_YAML) -> None:
        super().__init__(file_path)

    @override
    def parse(self) -> set[str]:
        """Parse pnpm-lock.yaml file and extract package names."""
        content = self.file_handler.read()
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in pnpm-lock.yaml: {e}") from e

        if not isinstance(data, dict):
            return set()

        packages: set[str] = set()

        # Parse root-level dependencies (if any)
        self._extract_from_pnpm_dependencies(data.get("dependencies", {}), packages)
        self._extract_from_pnpm_dependencies(data.get("devDependencies", {}), packages)
        self._extract_from_pnpm_dependencies(data.get("optionalDependencies", {}), packages)

        # Parse packages section (all resolved packages)
        self._extract_from_packages(data.get("packages", {}), packages)

        # Parse importers section (workspace packages)
        importers = data.get("importers", {})
        if isinstance(importers, dict):
            for importer_data in importers.values():
                if isinstance(importer_data, dict):
                    self._extract_from_pnpm_dependencies(importer_data.get("dependencies", {}), packages)
                    self._extract_from_pnpm_dependencies(importer_data.get("devDependencies", {}), packages)
                    self._extract_from_pnpm_dependencies(importer_data.get("optionalDependencies", {}), packages)

        return packages

    def _extract_from_pnpm_dependencies(self, deps: dict[str, Any], packages: set[str]) -> None:
        """Extract package names from pnpm-lock.yaml dependencies section.

        In pnpm-lock.yaml, dependencies have the format:
        {
            "package-name": {
                "specifier": "^1.0.0",
                "version": "1.0.0"
            }
        }
        """
        if not isinstance(deps, dict):
            return

        for dep_name, _dep_info in deps.items():
            if isinstance(dep_name, str):
                # Handle scoped packages (@scope/package)
                normalized_name = self._normalize_package_name(dep_name)
                if normalized_name:
                    packages.add(normalized_name)

    def _extract_from_packages(self, packages_section: dict[str, Any], packages: set[str]) -> None:
        """Extract package names from packages section.

        In pnpm-lock.yaml v9+, package keys are in the format:
        - @scope/package@1.0.0
        - package@1.0.0
        """
        if not isinstance(packages_section, dict):
            return

        for package_key in packages_section:
            if isinstance(package_key, str):
                # Package keys are in format: package@version or @scope/package@version
                package_name = self._extract_package_name_from_key(package_key)
                if package_name:
                    normalized_name = self._normalize_package_name(package_name)
                    if normalized_name:
                        packages.add(normalized_name)

    def _extract_package_name_from_key(self, package_key: str) -> str | None:
        """Extract package name from package key.

        In pnpm-lock.yaml v9+, package keys are in formats like:
        - @scope/package@1.0.0
        - package@1.0.0
        - @scope/package@1.0.0_peer-dep@1.0.0

        """
        if not package_key:
            return None

        # Handle scoped packages (@scope/package@version)
        if package_key.startswith("@"):
            # Pattern: @scope/package@version or @scope/package@version_peer-deps
            match = self._SCOPED_PACKAGE_PATTERN.match(package_key)
            if match:
                return match.group(1)
        else:
            # Pattern: package@version or package@version_peer-deps
            match = self._REGULAR_PACKAGE_PATTERN.match(package_key)
            if match:
                return match.group(1)

        return None

    def _normalize_package_name(self, name: str) -> str | None:
        """Normalize package name by removing invalid characters."""
        if not name or not isinstance(name, str):
            return None

        # Remove any trailing whitespace and validate
        normalized = name.strip()

        # Basic validation for npm package names
        if not normalized or len(normalized) > 214:
            return None

        # Check for valid npm package name characters
        # Allow letters, numbers, hyphens, underscores, dots, and scoped packages
        if not self._PACKAGE_NAME_VALIDATION_PATTERN.match(normalized):
            return None

        return normalized
