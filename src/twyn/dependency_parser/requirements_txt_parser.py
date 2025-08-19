"""Parser for requirements.txt dependencies."""

from typing import TYPE_CHECKING

from dparse import filetypes, parse

from twyn.dependency_parser.abstract_parser import AbstractParser

if TYPE_CHECKING:
    from dparse.dependencies import Dependency, DependencyFile


class RequirementsTxtParser(AbstractParser):
    """Parser for requirements.txt dependencies."""

    def __init__(self, file_path: str = filetypes.requirements_txt) -> None:
        super().__init__(file_path)

    def parse(self) -> set[str]:
        """Parse requirements.txt dependencies into set of dependency names."""
        dependency_file: DependencyFile = parse(self._read(), file_type=filetypes.requirements_txt)
        dependencies: list[Dependency] = dependency_file.resolved_dependencies
        return {dependency.name for dependency in dependencies}
