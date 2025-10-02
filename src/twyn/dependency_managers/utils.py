from twyn.dependency_managers.exceptions import NoMatchingDependencyManagerError
from twyn.dependency_managers.managers.base import BaseDependencyManager
from twyn.dependency_managers.managers.npm_dependency_manager import NpmDependencyManager
from twyn.dependency_managers.managers.pypi_dependency_manager import PypiDependencyManager

DEPENDENCY_MANAGERS: list[type[BaseDependencyManager]] = [
    PypiDependencyManager,
    NpmDependencyManager,
]
"""List of available dependency manager classes."""

PACKAGE_ECOSYSTEMS = {x.name for x in DEPENDENCY_MANAGERS}
"""Set of package ecosystem names from available dependency managers."""


def get_dependency_manager_from_file(dependency_file: str) -> type[BaseDependencyManager]:
    """Get dependency manager that can handle the given file."""
    for manager in DEPENDENCY_MANAGERS:
        if manager.matches_dependency_file(dependency_file):
            return manager
    raise NoMatchingDependencyManagerError


def get_dependency_manager_from_name(name: str) -> type[BaseDependencyManager]:
    """Get dependency manager by ecosystem name."""
    for manager in DEPENDENCY_MANAGERS:
        if manager.matches_ecosystem_name(name):
            return manager
    raise NoMatchingDependencyManagerError
