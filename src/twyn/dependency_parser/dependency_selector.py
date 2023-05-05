import logging
from typing import Optional

from twyn.base.constants import DEPENDENCY_FILE_MAPPING
from twyn.dependency_parser.abstract_parser import AbstractParser
from twyn.dependency_parser.exceptions import (
    MultipleParsersError,
    NoMatchingParserError,
)

logger = logging.getLogger()


class DependencySelector:
    def __init__(self, dependency_file: Optional[str] = None) -> None:
        self.dependency_file = dependency_file or ""

    @staticmethod
    def _raise_for_selected_parsers(parsers) -> None:
        if len(parsers) > 1:
            raise MultipleParsersError

        if not parsers:
            raise NoMatchingParserError

    def auto_detect_dependency_file_parser(self) -> type[AbstractParser]:
        parsers = [
            dependency_parser
            for dependency_parser in DEPENDENCY_FILE_MAPPING.values()
            if dependency_parser().file_exists()
        ]
        self._raise_for_selected_parsers(parsers)
        logger.debug("Dependencies file found")
        return parsers[0]

    def get_dependency_file_parser_from_file_name(
        self,
    ) -> type[AbstractParser]:
        parsers = []
        for known_dependency_file_name in DEPENDENCY_FILE_MAPPING:
            if self.dependency_file.endswith(known_dependency_file_name):
                parsers.append(DEPENDENCY_FILE_MAPPING[known_dependency_file_name])

        self._raise_for_selected_parsers(parsers)
        return parsers[0]

    def get_dependency_parser(self) -> AbstractParser:
        logger.debug(f"Dependency file: {self.dependency_file}")

        if self.dependency_file:
            logger.debug("Dependency file provided. Assigning a parser.")
            dependency_file_parser = self.get_dependency_file_parser_from_file_name()
        else:
            logger.debug("No dependency file provided. Attempting to locate one.")
            dependency_file_parser = self.auto_detect_dependency_file_parser()

        file_parser = dependency_file_parser()
        logger.debug(f"Assigned {file_parser} parser for local dependencies file.")
        file_parser.raise_for_valid_file()

        return file_parser
