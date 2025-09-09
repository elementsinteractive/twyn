from dataclasses import dataclass
from pathlib import Path

from twyn.dependency_managers.exceptions import NoMatchingDependencyManagerError
from twyn.dependency_parser.parsers.constants import PACKAGE_LOCK_JSON, POETRY_LOCK, REQUIREMENTS_TXT, UV_LOCK
from twyn.trusted_packages.references import AbstractPackageReference, TopNpmReference, TopPyPiReference


@dataclass
class BaseDependencyManager:
    """Base class for all `DependencyManagers`.

    It acts as a repository, linking programming languages with trusted packages sources and dependency file names.
    """

    name: str
    trusted_packages_source: type[AbstractPackageReference]
    dependency_files: set[str]

    @classmethod
    def matches_dependency_file(cls, dependency_file: str) -> bool:
        return Path(dependency_file).name in cls.dependency_files

    @classmethod
    def matches_language_name(cls, name: str) -> bool:
        return cls.name == Path(name).name.lower()


@dataclass
class PypiDependencyManager(BaseDependencyManager):
    name = "pypi"
    trusted_packages_source = TopPyPiReference
    dependency_files = {UV_LOCK, POETRY_LOCK, REQUIREMENTS_TXT}


@dataclass
class NpmDependencyManager(BaseDependencyManager):
    name = "npm"
    trusted_packages_source = TopNpmReference
    dependency_files = {PACKAGE_LOCK_JSON}


DEPENDENCY_MANAGERS: list[type[BaseDependencyManager]] = [PypiDependencyManager, NpmDependencyManager]
PACKAGE_ECOSYSTEMS = {x.name for x in DEPENDENCY_MANAGERS}


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
