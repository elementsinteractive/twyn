from dataclasses import dataclass

from twyn.dependency_managers.managers.base import BaseDependencyManager
from twyn.dependency_parser.parsers.constants import PACKAGE_LOCK_JSON, YARN_LOCK
from twyn.trusted_packages import TopNpmReference


@dataclass
class NpmDependencyManager(BaseDependencyManager):
    name = "npm"
    trusted_packages_source = TopNpmReference
    dependency_files = {PACKAGE_LOCK_JSON, YARN_LOCK}
