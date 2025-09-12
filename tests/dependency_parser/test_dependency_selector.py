from unittest.mock import Mock, patch

import pytest
from twyn.dependency_parser import PoetryLockParser, RequirementsTxtParser, UvLockParser
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.dependency_parser.exceptions import (
    NoMatchingParserError,
)
from twyn.dependency_parser.parsers.abstract_parser import AbstractParser


class TestDependencySelector:
    @pytest.mark.parametrize(
        ("file_name", "parser_class"),
        [
            (
                "requirements.txt",
                RequirementsTxtParser,
            ),  # because file is specified, we won't autocheck
            ("poetry.lock", PoetryLockParser),
            ("uv.lock", UvLockParser),
            ("/some/path/poetry.lock", PoetryLockParser),
            ("/some/path/uv.lock", UvLockParser),
            ("/some/path/requirements.txt", RequirementsTxtParser),
        ],
    )
    def test_get_dependency_parser(self, file_name: str, parser_class: type[AbstractParser]):
        parser = DependencySelector(file_name).get_dependency_parsers()
        assert len(parser) == 1

        assert isinstance(parser[0], parser_class)
        assert str(parser[0].file_handler.file_path).endswith(file_name)

    @patch("twyn.dependency_parser.parsers.lock_parser.PoetryLockParser.file_exists")
    @patch("twyn.dependency_parser.parsers.lock_parser.UvLockParser.file_exists")
    @patch("twyn.dependency_parser.parsers.requirements_txt_parser.RequirementsTxtParser.file_exists")
    def test_get_dependency_parser_auto_detect_requirements_file(
        self, req_file_exists: Mock, uv_file_exists: Mock, poetry_file_exists: Mock
    ):
        poetry_file_exists.return_value = False
        req_file_exists.return_value = True
        uv_file_exists.return_value = False

        parser = DependencySelector("").get_dependency_parsers()
        assert isinstance(parser[0], RequirementsTxtParser)

    @patch("twyn.dependency_parser.parsers.lock_parser.PoetryLockParser.file_exists")
    @patch("twyn.dependency_parser.parsers.lock_parser.UvLockParser.file_exists")
    @patch("twyn.dependency_parser.parsers.requirements_txt_parser.RequirementsTxtParser.file_exists")
    def test_get_dependency_parser_auto_detect_poetry_lock_file(
        self, req_file_exists: Mock, uv_file_exists: Mock, poetry_file_exists: Mock
    ) -> None:
        poetry_file_exists.return_value = True
        req_file_exists.return_value = False
        uv_file_exists.return_value = False

        selector = DependencySelector("")
        parser = selector.get_dependency_parsers()
        assert isinstance(parser[0], PoetryLockParser)

    @patch("twyn.dependency_parser.parsers.lock_parser.PoetryLockParser.file_exists")
    @patch("twyn.dependency_parser.parsers.lock_parser.UvLockParser.file_exists")
    @patch("twyn.dependency_parser.parsers.requirements_txt_parser.RequirementsTxtParser.file_exists")
    def test_get_dependency_parser_auto_detect_uv_lock_file(
        self, req_file_exists: Mock, uv_file_exists: Mock, poetry_file_exists: Mock
    ) -> None:
        poetry_file_exists.return_value = False
        req_file_exists.return_value = False
        uv_file_exists.return_value = True

        parser = DependencySelector("").get_dependency_parsers()
        assert isinstance(parser[0], UvLockParser)

    @patch("twyn.dependency_parser.parsers.abstract_parser.AbstractParser.file_exists")
    def test_auto_detect_dependency_file_parser_exceptions(self, file_exists: Mock) -> None:
        file_exists.return_value = False
        with pytest.raises(NoMatchingParserError):
            DependencySelector().get_dependency_parsers()

    @pytest.mark.parametrize("file_name", ["unknown.txt", ""])
    def test_get_dependency_file_parser_unknown_file_type(self, file_name: str) -> None:
        with pytest.raises(NoMatchingParserError):
            DependencySelector(file_name).get_dependency_file_parsers_from_file_name()
