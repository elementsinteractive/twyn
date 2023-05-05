import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from twyn.base.exceptions import TwynError
from twyn.dependency_parser.exceptions import (
    PathIsNotFileError,
    PathNotFoundError,
)

logger = logging.getLogger()


class AbstractParser(ABC):
    def __init__(self, file_path: str = "") -> None:
        self.file_path = Path(os.path.abspath(os.path.join(os.getcwd(), file_path)))

    def __str__(self):
        return self.__class__.__name__

    def _read(self) -> str:
        content = self.file_path.read_text()
        logger.debug("Successfully read content from local dependencies file")

        return content

    def file_exists(self) -> bool:
        try:
            self.raise_for_valid_file()
        except TwynError:
            return False
        return True

    def raise_for_valid_file(self) -> None:
        if not self.file_path.exists():
            raise PathNotFoundError

        if not self.file_path.is_file():
            raise PathIsNotFileError

    @abstractmethod
    def parse(self) -> set[str]:
        """
        Parse text into dependencies set.

        Parse the file's contents into a set of dependency names (type: str).
        All data other than the dependency names (e.g. whether a dependency is
        a dev dependency or main dependency; version constraints) is omitted.
        """
