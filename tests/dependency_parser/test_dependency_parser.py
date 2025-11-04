from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from twyn.dependency_parser import (
    PackageLockJsonParser,
    PnpmLockParser,
    PoetryLockParser,
    RequirementsTxtParser,
    UvLockParser,
)
from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.yarn_lock_parser import YarnLockParser


class TestAbstractParser:
    class TemporaryParser(AbstractParser):
        """Subclass of AbstractParser to test methods."""

        def parse(self) -> set[str]:
            self._read()
            return set()

    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_file_exists(self, mock_is_file: Mock, mock_exists: Mock, mock_stat: Mock) -> None:
        mock_exists.return_value = True
        mock_is_file.return_value = True

        mock_stat_result = Mock()
        mock_stat_result.st_size = 100
        mock_stat.return_value = mock_stat_result

        parser = self.TemporaryParser("fake_path.txt")
        assert parser.file_exists() is True

    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @pytest.mark.parametrize(
        ("file_exists", "is_file", "file_size"),
        [
            (False, False, 100),
            (True, False, 100),
            (True, True, 0),
        ],
    )
    def test_raise_for_valid_file(
        self,
        mock_is_file: Mock,
        mock_exists: Mock,
        mock_stat: Mock,
        file_exists: bool,
        is_file: bool,
        file_size: int,
    ) -> None:
        mock_exists.return_value = file_exists
        mock_is_file.return_value = is_file

        mock_stat_result = Mock()
        mock_stat_result.st_size = file_size
        mock_stat.return_value = mock_stat_result

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


class TestYarnLockParser:
    def test_parse_yarn_lock_v1(self, yarn_lock_file_v1: Path) -> None:
        parser = YarnLockParser(file_path=str(yarn_lock_file_v1))

        assert parser.parse() == {"lodash", "react", "react-dom", "@babel/helper-plugin-utils"}

    def test_parse_yarn_lock_v2(self, yarn_lock_file_v2: Path) -> None:
        parser = YarnLockParser(file_path=str(yarn_lock_file_v2))

        assert parser.parse() == {"dependencies", "react-dom", "lodash", "version", "cacheKey", "resolution", "react"}


class TestPnpmLockParser:
    def test_parse_pnpm_lock_v9(self, pnpm_lock_file_v9: Path) -> None:
        parser = PnpmLockParser(file_path=str(pnpm_lock_file_v9))
        result = parser.parse()

        # Should find all dependencies from the v9 fixture
        expected_packages = {
            "react",
            "react-dom",
            "lodash",
            "@babel/core",
            "@babel/helper-plugin-utils",
            "express",
            "debug",
            "typescript",
            "@types/node",
        }
        assert expected_packages == result

        # Should not include workspace projects
        assert "test-project" not in result
        assert "my-workspace" not in result
