"""Parser for poetry.lock dependencies."""


from dparse import filetypes, parse
from dparse.dependencies import Dependency, DependencyFile

from twyn.dependency_parser.abstract_parser import AbstractParser


class PoetryLockParser(AbstractParser):
    """Parser for poetry.lock."""

    def __init__(self, file_path: str = filetypes.poetry_lock) -> None:
        super().__init__(file_path)

    def parse(self) -> set[str]:
        """Parse poetry.lock dependencies into set of dependency names."""
        dependency_file: DependencyFile = parse(
            self._read(), file_type=filetypes.poetry_lock
        )
        dependencies: list[Dependency] = dependency_file.resolved_dependencies
        return {dependency.name for dependency in dependencies}
