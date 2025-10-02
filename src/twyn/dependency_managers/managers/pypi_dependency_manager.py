from dataclasses import dataclass

from twyn.dependency_managers.managers.base import BaseDependencyManager
from twyn.dependency_parser.parsers.constants import POETRY_LOCK, REQUIREMENTS_TXT, UV_LOCK
from twyn.trusted_packages import TopPyPiReference


@dataclass
class PypiDependencyManager(BaseDependencyManager):
    name = "pypi"
    """Name of the PyPI package ecosystem."""
    trusted_packages_source = TopPyPiReference
    """Reference source for trusted PyPI packages."""
    dependency_files = {UV_LOCK, POETRY_LOCK, REQUIREMENTS_TXT}
    """Set of supported Python dependency file names."""
