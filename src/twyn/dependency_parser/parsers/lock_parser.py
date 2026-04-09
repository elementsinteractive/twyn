import tomlkit
import tomlkit.exceptions

from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.constants import POETRY_LOCK, UV_LOCK
from twyn.dependency_parser.parsers.exceptions import InvalidFileFormatError


class TomlLockParser(AbstractParser):
    """Parser for TOML-based lock files."""

    def parse(self) -> set[str]:
        """Parse dependencies names and map them to a set."""
        try:
            data = tomlkit.parse(self.file_handler.read())
        except tomlkit.exceptions.ParseError as e:
            raise InvalidFileFormatError("Invalid YAML format.") from e

        packages = data.get("package", [])
        return {pkg["name"] for pkg in packages if isinstance(pkg, dict) and "name" in pkg}


class PoetryLockParser(TomlLockParser):
    """Parser for poetry.lock files."""

    def __init__(self, file_path: str = POETRY_LOCK) -> None:
        super().__init__(file_path)


class UvLockParser(TomlLockParser):
    """Parser for uv.lock files."""

    def __init__(self, file_path: str = UV_LOCK) -> None:
        super().__init__(file_path)
