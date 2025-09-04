import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from twyn.file_handler.file_handler import FileHandler

logger = logging.getLogger("twyn")


class AbstractParser(ABC):
    """
    Abstract class for file parsers.

    Provides basic methods to deal with the dependecies file.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(os.path.abspath(os.path.join(os.getcwd(), file_path)))
        self.file_handler = FileHandler(file_path=self.file_path)

    def __str__(self) -> str:
        return self.__class__.__name__

    def _read(self) -> str:
        return self.file_handler.read()

    def file_exists(self) -> bool:
        return self.file_handler.exists()

    @abstractmethod
    def parse(self) -> set[str]:
        """
        Parse text into dependencies set.

        Parse the file's contents into a set of dependency names (type: str).
        All data other than the dependency names (e.g. whether a dependency is
        a dev dependency or main dependency; version constraints) is omitted.
        """
