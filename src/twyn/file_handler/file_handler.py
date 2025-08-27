import logging
import os
from pathlib import Path
from typing import Protocol

from twyn.file_handler.exceptions import PathIsNotFileError, PathNotFoundError

logger = logging.getLogger("twyn")


class BaseFileHandler(Protocol):
    def read(self) -> str: ...
    def exists(self) -> bool: ...
    def write(self, data: str) -> None: ...
    def delete(self, remove_parent_dir: bool) -> None: ...


class FileHandler(BaseFileHandler):
    def __init__(self, file_path: str) -> None:
        self.file_path = self._get_file_path(file_path)

    def _get_file_path(self, file_path: str) -> Path:
        return Path(os.path.abspath(os.path.join(os.getcwd(), file_path)))

    def is_handler_of_file(self, name: str) -> bool:
        return self._get_file_path(name) == self.file_path

    def read(self) -> str:
        self._raise_for_file_exists()

        content = self.file_path.read_text()
        logger.debug("Successfully read content from local dependencies file")

        return content

    def exists(self) -> bool:
        try:
            self._raise_for_file_exists()
        except (PathNotFoundError, PathIsNotFileError):
            return False
        return True

    def _raise_for_file_exists(self) -> None:
        if not self.file_path.exists():
            raise PathNotFoundError

        if not self.file_path.is_file():
            raise PathIsNotFileError

    def write(self, data: str) -> None:
        self.file_path.write_text(data)

    def delete(self, delete_parent_dir: bool = False) -> None:
        if not self.exists():
            logger.info("File does not exist, nothing to delete")
            return

        self.file_path.unlink()
        logger.info("Deleted file: %s", self.file_path)

        if delete_parent_dir:
            try:
                self.file_path.parent.rmdir()
                logger.info("Removed empty directory: %s", self.file_path.parent)
            except OSError:
                logger.exception(
                    "Directory not empty or not enough permissions. Cannot be removed: %s", self.file_path.parent
                )
