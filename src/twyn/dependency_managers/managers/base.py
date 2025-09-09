from dataclasses import dataclass
from pathlib import Path

from twyn.trusted_packages.references.base import AbstractPackageReference


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
