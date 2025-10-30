from unittest.mock import Mock

from twyn.dependency_managers.managers import DependencyManager

manager = DependencyManager(
    name="pypi", trusted_packages_source=Mock(), dependency_files={"requirements.txt", "poetry.lock"}
)


class TestDependencyManager:
    def test_matches_dependency_file(self) -> None:
        assert manager.matches_dependency_file("requirements.txt")
        assert manager.matches_dependency_file("/some/path/poetry.lock")
        assert not manager.matches_dependency_file("setup.py")

    def test_get_alternative_source_none(self) -> None:
        sources = {"npm": "npmjs.com"}
        assert manager.get_alternative_source(sources) is None
