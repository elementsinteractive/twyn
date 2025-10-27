from dataclasses import dataclass
from pathlib import Path

from twyn.trusted_packages.references.base import AbstractPackageReference


@dataclass
class BaseDependencyManager:
    """Base class for all `DependencyManagers`.

    It acts as a repository, linking programming languages with trusted packages sources and dependency file names.
    """

    name: str
    """Name identifier for the package ecosystem."""
    trusted_packages_source: type[AbstractPackageReference]
    """Reference class for trusted packages source."""
    dependency_files: set[str]
    """Set of supported dependency file names."""

    @classmethod
    def matches_dependency_file(cls, dependency_file: str) -> bool:
        """Check if this manager can handle the given dependency file."""
        return Path(dependency_file).name in cls.dependency_files

    @classmethod
    def matches_ecosystem_name(cls, name: str) -> bool:
        """Check if this manager matches the given ecosystem name."""
        return cls.name == Path(name).name.lower()

    @classmethod
    def get_alternative_source(cls, sources: dict[str, str]) -> str | None:
        """Get alternative source URL for this ecosystem from sources dict."""
        match = [x for x in sources if x == cls.name]

        return sources[match[0]] if match else None
