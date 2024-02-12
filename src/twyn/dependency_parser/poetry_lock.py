"""Parser for poetry.lock dependencies."""

import tomllib
from dparse import filetypes

from twyn.dependency_parser.abstract_parser import AbstractParser


class PoetryLockParser(AbstractParser):
    """Parser for poetry.lock."""

    def __init__(self, file_path: str = filetypes.poetry_lock) -> None:
        super().__init__(file_path)

    def parse(self) -> set[str]:
        """Parse poetry.lock dependencies into set of dependency names."""
        data = tomllib.loads(self._read())
        return {dependency["name"] for dependency in data["package"]}
