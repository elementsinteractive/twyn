import logging
from pathlib import Path
from typing import Optional

from twyn.base.constants import DEPENDENCY_FILE_MAPPING
from twyn.dependency_parser.exceptions import (
    NoMatchingParserError,
)
from twyn.dependency_parser.parsers.abstract_parser import AbstractParser

logger = logging.getLogger("twyn")


class DependencySelector:
    def __init__(self, dependency_files: Optional[set[str]] = None, root_path: str = ".") -> None:
        self.dependency_files = dependency_files or set()
        self.root_path = root_path

    def auto_detect_dependency_file_parser(self) -> list[AbstractParser]:
        parsers: list[AbstractParser] = []
        root = Path(self.root_path)
        for path in root.rglob("*"):
            if ".git" in path.parts:
                continue
            if path.is_file():
                for known_file, dependency_parser in DEPENDENCY_FILE_MAPPING.items():
                    if path.name == known_file:
                        file_parser = dependency_parser(str(path))
                        if file_parser.file_exists():
                            parsers.append(file_parser)
                            logger.debug("Assigned %s parser for local dependencies file at %s.", file_parser, path)

        if not parsers:
            raise NoMatchingParserError

        logger.debug("Dependencies file(s) found: %s", [str(p.file_path) for p in parsers])
        return parsers

    def get_dependency_file_parsers_from_file_name(self) -> list[AbstractParser]:
        parsers = []
        for dependency_file in self.dependency_files:
            for known_dependency_file_name in DEPENDENCY_FILE_MAPPING:
                if dependency_file.endswith(known_dependency_file_name):
                    file_parser = DEPENDENCY_FILE_MAPPING[known_dependency_file_name](dependency_file)
                    parsers.append(file_parser)
        if not parsers:
            raise NoMatchingParserError

        return parsers

    def get_dependency_parsers(self) -> list[AbstractParser]:
        if self.dependency_files:
            logger.debug("Dependency file provided. Assigning a parser.")
            return self.get_dependency_file_parsers_from_file_name()

        logger.debug("No dependency file provided. Attempting to locate one.")
        return self.auto_detect_dependency_file_parser()
