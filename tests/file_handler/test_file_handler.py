from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from twyn.file_handler.exceptions import PathIsNotFileError
from twyn.file_handler.file_handler import FileHandler


class TestFileHandler:
    def test_file_exists(self, pyproject_toml_file: Path) -> None:
        parser = FileHandler(pyproject_toml_file)
        assert parser.exists() is True

    def test_read_file_success(self, pyproject_toml_file: Path) -> None:
        parser = FileHandler(pyproject_toml_file)
        read = parser.read()
        assert len(read) > 1
        assert isinstance(read, str)

    def test_read_file_does_not_exist(
        self,
    ):
        parser = FileHandler("")
        with pytest.raises(PathIsNotFileError):
            parser.read()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @pytest.mark.parametrize(
        ("file_exists", "is_file"),
        [(False, False), (True, False)],
    )
    def test_raise_for_valid_file(
        self, mock_is_file: Mock, mock_exists: Mock, file_exists: bool, is_file: bool
    ) -> None:
        mock_exists.return_value = file_exists
        mock_is_file.return_value = is_file

        parser = FileHandler("fake.txt")
        assert parser.exists() is False
