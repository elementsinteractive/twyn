from unittest.mock import patch

import pytest
from twyn.file_handler.exceptions import PathIsNotFileError, PathNotFoundError
from twyn.file_handler.file_handler import FileHandlerPathlib


class TestFileHandlerPathlib:
    def test_file_exists(self, pyproject_toml_file: str):
        parser = FileHandlerPathlib(pyproject_toml_file)
        assert parser.file_exists() is True

    def test_read_file_success(self, pyproject_toml_file: str):
        parser = FileHandlerPathlib(pyproject_toml_file)
        read = parser.read()
        assert len(read) > 1
        assert isinstance(read, str)

    def test_read_file_does_not_exist(
        self,
    ):
        parser = FileHandlerPathlib("")
        with pytest.raises(PathIsNotFileError):
            parser.read()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @pytest.mark.parametrize(
        "file_exists, is_file, exception",
        [[False, False, PathNotFoundError], [True, False, PathIsNotFileError]],
    )
    def test_raise_for_valid_file(self, mock_is_file, mock_exists, file_exists, is_file, exception):
        mock_exists.return_value = file_exists
        mock_is_file.return_value = is_file

        parser = FileHandlerPathlib("fake.txt")
        assert parser.file_exists() is False
