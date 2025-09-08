from twyn.dependency_managers.exceptions import NoMatchingDependencyManagerError
from twyn.dependency_managers.managers.base import BaseDependencyManager
from twyn.dependency_managers.managers.npm_dependency_manager import NpmDependencyManager
from twyn.dependency_managers.managers.pypi_dependency_manager import PypiDependencyManager


def get_dependency_manager_from_file(dependency_file: str) -> type[BaseDependencyManager]:
    for manager in DEPENDENCY_MANAGERS:
        if manager.matches_dependency_file(dependency_file):
            return manager
    raise NoMatchingDependencyManagerError


def get_dependency_manager_from_name(name: str) -> type[BaseDependencyManager]:
    for manager in DEPENDENCY_MANAGERS:
        if manager.matches_language_name(name):
            return manager
    raise NoMatchingDependencyManagerError


DEPENDENCY_MANAGERS: list[type[BaseDependencyManager]] = [
    PypiDependencyManager,
    NpmDependencyManager,
]
PACKAGE_ECOSYSTEMS = {x.name for x in DEPENDENCY_MANAGERS}
