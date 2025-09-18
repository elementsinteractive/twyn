from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
    def matches_ecosystem_name(cls, name: str) -> bool:
        return cls.name == Path(name).name.lower()

    @classmethod
    def get_alternative_source(cls, sources: dict[str, str]) -> Optional[str]:
        match = [x for x in sources if x == cls.name]

        return sources[match[0]] if match else None
