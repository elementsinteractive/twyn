from dataclasses import dataclass
from pathlib import Path

from twyn.dependency_managers.exceptions import NoMatchingDependencyManagerError
from twyn.dependency_parser.parsers.constants import (
    PACKAGE_LOCK_JSON,
    POETRY_LOCK,
    REQUIREMENTS_TXT,
    UV_LOCK,
    YARN_LOCK,
)
from twyn.trusted_packages.managers.base import TrustedPackagesProtocol
from twyn.trusted_packages.managers.trusted_npm_packages_manager import TrustedNpmPackageManager
from twyn.trusted_packages.managers.trusted_pypi_packages_manager import TrustedPackages
from twyn.trusted_packages.references.base import AbstractPackageReference
from twyn.trusted_packages.references.top_npm_reference import TopNpmReference
from twyn.trusted_packages.references.top_pypi_reference import TopPyPiReference


@dataclass
class DependencyManager:
    """Base class for all `DependencyManagers`.

    It acts as a repository, linking programming languages with trusted packages sources and dependency file names.
    """

    name: str
    """Name identifier for the package ecosystem."""

    trusted_packages_source: type[AbstractPackageReference]
    """Reference class for trusted packages source."""

    dependency_files: set[str]
    """Set of supported dependency file names."""

    trusted_packages_manager: type[TrustedPackagesProtocol]
    """TrustedPackages class that will determine if there's a typo or not."""

    def matches_dependency_file(self, dependency_file: str) -> bool:
        """Check if this manager can handle the given dependency file."""
        return Path(dependency_file).name in self.dependency_files

    def get_alternative_source(self, sources: dict[str, str]) -> str | None:
        """Get alternative source URL for this ecosystem from sources dict."""
        return sources.get(self.name)


npm_dependency_manager = DependencyManager(
    name="npm",
    trusted_packages_source=TopNpmReference,
    dependency_files={PACKAGE_LOCK_JSON, YARN_LOCK},
    trusted_packages_manager=TrustedNpmPackageManager,
)
pypi_dependency_manager = DependencyManager(
    name="pypi",
    trusted_packages_source=TopPyPiReference,
    dependency_files={UV_LOCK, POETRY_LOCK, REQUIREMENTS_TXT},
    trusted_packages_manager=TrustedPackages,
)


DEPENDENCY_MANAGERS: list[DependencyManager] = [pypi_dependency_manager, npm_dependency_manager]
"""List of available dependency manager classes."""

PACKAGE_ECOSYSTEMS = {x.name for x in DEPENDENCY_MANAGERS}
"""Set of package ecosystem names from available dependency managers."""


def get_dependency_manager_from_file(dependency_file: str) -> DependencyManager:
    """Get dependency manager that can handle the given file."""
    for manager in DEPENDENCY_MANAGERS:
        if manager.matches_dependency_file(dependency_file):
            return manager
    raise NoMatchingDependencyManagerError


def get_dependency_manager_from_name(name: str) -> DependencyManager:
    """Get dependency manager by ecosystem name."""
    for manager in DEPENDENCY_MANAGERS:
        if manager.name == name:
            return manager
    raise NoMatchingDependencyManagerError
