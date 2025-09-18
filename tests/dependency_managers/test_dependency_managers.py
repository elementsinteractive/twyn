from unittest.mock import Mock

from twyn.dependency_managers.managers.base import BaseDependencyManager


class DummyManager(BaseDependencyManager):
    name = "pypi"
    trusted_packages_source = Mock()
    dependency_files = {"requirements.txt", "poetry.lock"}


class TestDependencyManager:
    def test_matches_dependency_file(self) -> None:
        assert DummyManager.matches_dependency_file("requirements.txt")
        assert DummyManager.matches_dependency_file("/some/path/poetry.lock")
        assert not DummyManager.matches_dependency_file("setup.py")

    def test_matches_language_name(self) -> None:
        assert DummyManager.matches_ecosystem_name("pypi")
        assert not DummyManager.matches_ecosystem_name("npm")

    def test_get_alternative_source_none(self) -> None:
        sources = {"npm": "npmjs.com"}
        assert DummyManager.get_alternative_source(sources) is None
