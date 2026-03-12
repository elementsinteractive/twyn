from pathlib import Path

import pytest
from twyn.dependency_parser import (
    DockerComposeParser,
    DockerfileParser,
    PoetryLockParser,
    RequirementsTxtParser,
    UvLockParser,
)
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.dependency_parser.exceptions import (
    NoMatchingParserError,
)
from twyn.dependency_parser.parsers.abstract_parser import AbstractParser
from twyn.dependency_parser.parsers.package_lock_json import PackageLockJsonParser
from twyn.dependency_parser.parsers.yarn_lock_parser import YarnLockParser


class TestDependencySelector:
    @pytest.mark.parametrize(
        ("file_name", "parser_class"),
        [
            ("requirements.txt", RequirementsTxtParser),
            ("poetry.lock", PoetryLockParser),
            ("uv.lock", UvLockParser),
            ("yarn.lock", YarnLockParser),
            ("package-lock.json", PackageLockJsonParser),
            ("Dockerfile", DockerfileParser),
            ("docker-compose.yml", DockerComposeParser),
            ("docker-compose.yaml", DockerComposeParser),
            ("compose.yml", DockerComposeParser),
            ("compose.yaml", DockerComposeParser),
        ],
    )
    def test_get_dependency_parser(self, file_name: str, parser_class: type[AbstractParser]) -> None:
        parser = DependencySelector({file_name}).get_dependency_parsers()
        assert len(parser) == 1

        assert isinstance(parser[0], parser_class)
        assert str(parser[0].file_handler.file_path).endswith(file_name)

    def test_get_dependency_parser_auto_detects_file(self, requirements_txt_file: Path, tmp_path: Path) -> None:
        parser = DependencySelector("", root_path=str(tmp_path)).get_dependency_parsers()
        assert isinstance(parser[0], RequirementsTxtParser)

    def test_auto_detect_dependency_file_parser_exceptions(self, tmp_path: Path) -> None:
        with pytest.raises(NoMatchingParserError):
            DependencySelector(root_path=str(tmp_path)).get_dependency_parsers()

    @pytest.mark.parametrize("file_name", ["unknown.txt", ""])
    def test_get_dependency_file_parser_unknown_file_type(self, file_name: str) -> None:
        with pytest.raises(NoMatchingParserError):
            DependencySelector({file_name}).get_dependency_parsers()

    def test_auto_detect_dependency_file_parser_scans_subdirectories(self, tmp_path: Path) -> None:
        # Create nested directories and dependency files
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        req_file = subdir / "requirements.txt"
        req_file.write_text("flask\n")
        poetry_file = tmp_path / "poetry.lock"
        poetry_file.write_text("[package]\nname = 'pytest'\n")

        # Should not scan .git
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        git_file = git_dir / "requirements.txt"
        git_file.write_text("should not be found\n")

        # Should find both files
        selector = DependencySelector(root_path=str(tmp_path))

        parsers = selector.auto_detect_dependency_file_parser()
        found_files = {str(p.file_path) for p in parsers}
        assert found_files == {str(poetry_file), str(req_file)}
