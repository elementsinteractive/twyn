import sys

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import POETRY_LOCK, UV_LOCK

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class TomlLockParser(AbstractParser):
    """Parser for TOML-based lock files."""

    def parse(self) -> set[str]:
        """Parse dependencies names and map them to a set."""
        data = tomllib.loads(self.file_handler.read())
        return {dependency["name"] for dependency in data["package"]}


class PoetryLockParser(TomlLockParser):
    """Parser for poetry.lock files."""

    def __init__(self, file_path: str = POETRY_LOCK) -> None:
        super().__init__(file_path)


class UvLockParser(TomlLockParser):
    """Parser for uv.lock files."""

    def __init__(self, file_path: str = UV_LOCK) -> None:
        super().__init__(file_path)
