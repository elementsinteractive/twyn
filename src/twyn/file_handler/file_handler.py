import logging
import os
from pathlib import Path
from typing import Protocol

from twyn.base.exceptions import TwynError
from twyn.file_handler.exceptions import PathIsNotFileError, PathNotFoundError

logger = logging.getLogger("twyn")


class BaseFileHandler(Protocol):
    def __init__(self, file_path: str) -> None: ...
    def read(self) -> str: ...
    def file_exists(self) -> bool: ...


class FileHandlerPathlib(BaseFileHandler):
    def __init__(self, file_path: str) -> None:
        self.file_path = Path(os.path.abspath(os.path.join(os.getcwd(), file_path)))

    def read(self) -> str:
        self._raise_for_file_exists()

        content = self.file_path.read_text()
        logger.debug("Successfully read content from local dependencies file")

        return content

    def file_exists(self) -> bool:
        try:
            self._raise_for_file_exists()
        except TwynError:
            return False
        return True

    def _raise_for_file_exists(self) -> None:
        if not self.file_path.exists():
            raise PathNotFoundError

        if not self.file_path.is_file():
            raise PathIsNotFileError
