from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from twyn.dependency_parser import PackageLockJsonParser, PoetryLockParser, RequirementsTxtParser, UvLockParser
from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.file_handler.exceptions import PathIsNotFileError, PathNotFoundError


class TestAbstractParser:
    class TemporaryParser(AbstractParser):
        """Subclass of AbstractParser to test methods."""

        def parse(self) -> set[str]:
            self._read()
            return set()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_file_exists(self, mock_exists: Mock, mock_is_file: Mock) -> None:
        mock_exists.return_value = True
        mock_is_file.return_value = True
        parser = self.TemporaryParser("fake_path.txt")
        assert parser.file_exists() is True

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @pytest.mark.parametrize(
        ("file_exists", "is_file", "exception"),
        [(False, False, PathNotFoundError), (True, False, PathIsNotFileError)],
    )
    def test_raise_for_valid_file(
        self, mock_is_file: Mock, mock_exists: Mock, file_exists: Mock, is_file, exception: Mock
    ):
        mock_exists.return_value = file_exists
        mock_is_file.return_value = is_file

        parser = self.TemporaryParser("fake_path.txt")
        assert parser.file_exists() is False


class TestRequirementsTxtParser:
    def test_parse_requirements_txt_file(self, requirements_txt_file: Path) -> None:
        parser = RequirementsTxtParser(file_path=requirements_txt_file)
        assert parser.parse() == {"South", "pycrypto", "Flask", "django", "requests", "urllib3"}


class TestLockParser:
    def test_parse_poetry_lock_file_lt_1_5(self, poetry_lock_file_lt_1_5: Path) -> None:
        parser = PoetryLockParser(file_path=poetry_lock_file_lt_1_5)
        assert parser.parse() == {"charset-normalizer", "flake8", "mccabe"}

    def test_parse_poetry_lock_file_ge_1_5(self, poetry_lock_file_ge_1_5: Path) -> None:
        parser = PoetryLockParser(file_path=poetry_lock_file_ge_1_5)
        assert parser.parse() == {"charset-normalizer", "flake8", "mccabe"}

    def test_uv_lock_parser(self, uv_lock_file: Path) -> None:
        parser = UvLockParser(file_path=uv_lock_file)
        assert parser.parse() == {"annotated-types", "anyio", "argcomplete"}


class TestPackageLockJsonParser:
    def test_parse_package_lock_json_file_v1(self, package_lock_json_file_v1: Path) -> None:
        parser = PackageLockJsonParser(file_path=package_lock_json_file_v1)
        result = parser.parse()
        # Should find all dependencies, including nested ones, from the v1 fixture
        assert "express" in result
        assert "body-parser" in result
        assert "debug" in result
        assert "test-project" not in result

    def test_parse_package_lock_json_file_v2(self, package_lock_json_file_v2: Path) -> None:
        parser = PackageLockJsonParser(file_path=package_lock_json_file_v2)
        result = parser.parse()
        # Should find all dependencies, including nested ones, from the fixture
        # Top-level: express
        # Nested: body-parser (under express), debug (under body-parser)
        assert "express" in result
        assert "body-parser" in result
        assert "debug" in result
        # Should not include the project name itself
        assert "test-project" not in result

    def test_parse_package_lock_json_file_v3(self, package_lock_json_file_v3: Path) -> None:
        parser = PackageLockJsonParser(file_path=package_lock_json_file_v3)
        result = parser.parse()
        # Should find all dependencies, including nested ones, from the v3 fixture
        assert "express" in result
        assert "body-parser" in result
        assert "debug" in result
        assert "test-project" not in result
