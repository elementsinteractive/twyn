from unittest.mock import patch

import pytest
from twyn.dependency_parser import PoetryLockParser, RequirementsTxtParser, UvLockParser
from twyn.dependency_parser.abstract_parser import AbstractParser
from twyn.file_handler.exceptions import PathIsNotFileError, PathNotFoundError


class TestAbstractParser:
    class TemporaryParser(AbstractParser):
        """Subclass of AbstractParser to test methods."""

        def parse(self) -> set[str]:
            self._read()
            return set()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_file_exists(self, _mock_exists, _mock_is_file):
        _mock_exists.return_value = True
        _mock_is_file.return_value = True
        parser = self.TemporaryParser("fake_path.txt")
        assert parser.file_exists() is True

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @pytest.mark.parametrize(
        "file_exists, is_file, exception",
        [[False, False, PathNotFoundError], [True, False, PathIsNotFileError]],
    )
    def test_raise_for_valid_file(self, mock_is_file, mock_exists, file_exists, is_file, exception):
        mock_exists.return_value = file_exists
        mock_is_file.return_value = is_file

        parser = self.TemporaryParser("fake_path.txt")
        assert parser.file_exists() is False


class TestRequirementsTxtParser:
    def test_parse_requirements_txt_file(self, requirements_txt_file):
        parser = RequirementsTxtParser(file_path=requirements_txt_file)
        assert parser.parse() == {"South", "pycrypto"}


class TestLockParser:
    def test_parse_poetry_lock_file_lt_1_5(self, poetry_lock_file_lt_1_5):
        parser = PoetryLockParser(file_path=poetry_lock_file_lt_1_5)
        assert parser.parse() == {"charset-normalizer", "flake8", "mccabe"}

    def test_parse_poetry_lock_file_ge_1_5(self, poetry_lock_file_ge_1_5):
        parser = PoetryLockParser(file_path=poetry_lock_file_ge_1_5)
        assert parser.parse() == {"charset-normalizer", "flake8", "mccabe"}

    def test_uv_lock_parser(self, uv_lock_file) -> None:
        parser = UvLockParser(file_path=uv_lock_file)
        assert parser.parse() == {"annotated-types", "anyio", "argcomplete"}
