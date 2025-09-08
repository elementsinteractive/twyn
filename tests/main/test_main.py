from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from tomlkit import dumps, parse
from twyn.config.config_handler import ConfigHandler, TwynConfiguration
from twyn.config.exceptions import InvalidSelectorMethodError
from twyn.dependency_managers.exceptions import NoMatchingDependencyManagerError
from twyn.dependency_managers.utils import (
    get_dependency_manager_from_file,
    get_dependency_manager_from_name,
)
from twyn.file_handler.file_handler import FileHandler
from twyn.main import (
    check_dependencies,
)
from twyn.trusted_packages import TopPyPiReference
from twyn.trusted_packages.exceptions import InvalidArgumentsError
from twyn.trusted_packages.trusted_packages import TyposquatCheckResult, TyposquatCheckResultList

from tests.conftest import create_tmp_file, patch_npm_packages_download


@pytest.mark.usefixtures("disable_track")
class TestCheckDependencies:
    @pytest.mark.parametrize(
        ("cli_config", "file_config", "expected_resolved_config"),
        [
            (
                {
                    "selector_method": "first-letter",
                    "dependency_file": "requirements.txt",
                    "use_cache": True,
                    "pypi_reference": "https://myurl.com",
                },
                {
                    "selector_method": "nearby-letter",
                    "dependency_file": "poetry.lock",
                    "allowlist": ["boto4", "boto2"],  # There is no allowlist option in the cli
                    "use_cache": False,
                    "pypi_reference": "https://mysecondurl.com",
                },
                TwynConfiguration(
                    dependency_file="requirements.txt",
                    selector_method="first-letter",
                    allowlist={"boto4", "boto2"},
                    source=TopPyPiReference.DEFAULT_SOURCE,
                    use_cache=True,
                    package_ecosystem="pypi",
                ),
            ),  # CLI args take precedence over config from file
            (
                {},
                {
                    "selector_method": "nearby-letter",
                    "dependency_file": "poetry.lock",
                    "allowlist": ["boto4", "boto2"],
                    "use_cache": False,
                    "pypi_reference": "https://mysecondurl.com",
                },
                TwynConfiguration(
                    dependency_file="poetry.lock",
                    selector_method="nearby-letter",
                    allowlist={"boto4", "boto2"},
                    source=TopPyPiReference.DEFAULT_SOURCE,
                    use_cache=False,
                    package_ecosystem="pypi",
                ),
            ),  # Config from file takes precendence over fallback values
            (
                {},
                {},
                TwynConfiguration(
                    dependency_file=None,
                    selector_method="all",
                    allowlist=set(),
                    source=TopPyPiReference.DEFAULT_SOURCE,
                    use_cache=True,
                    package_ecosystem="pypi",
                ),
            ),  # Fallback values
        ],
    )
    def test_options_priorities_assignation(
        self,
        cli_config: dict[str, Any],
        file_config: dict[str, Any],
        expected_resolved_config: TwynConfiguration,
    ) -> None:
        """
        Checks that the configuration values are picked accordingly to the priority they have.

        Relevance order:
        1. command line
        2. config file
        3. default values

        """
        handler = ConfigHandler(FileHandler(""))

        with patch.object(handler, "_read_toml", return_value=parse(dumps({"tool": {"twyn": file_config}}))):
            resolved = handler.resolve_config(
                selector_method=cli_config.get("selector_method"),
                dependency_file=cli_config.get("dependency_file"),
                use_cache=cli_config.get("use_cache"),
            )

        assert resolved.dependency_file == expected_resolved_config.dependency_file
        assert resolved.selector_method == expected_resolved_config.selector_method
        assert resolved.allowlist == expected_resolved_config.allowlist
        assert resolved.use_cache == expected_resolved_config.use_cache

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_detects_typosquats_from_file(
        self, mock_get_packages: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        """Check that dependencies are loaded from file, retrieved from source, and a typosquat is detected."""
        mock_get_packages.return_value = {"requests"}

        error = check_dependencies(
            dependency_file=str(uv_lock_file_with_typo),
            use_cache=False,
        )

        assert mock_get_packages.call_count == 1
        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="reqests", similars=["requests"])]
        )

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_detects_typosquats_from_file_and_language_is_set(
        self, mock_get_packages: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        """Check that dependencies are loaded from file, retrieved from source, and a typosquat is detected."""
        mock_get_packages.return_value = {"requests"}

        error = check_dependencies(
            dependency_file=str(uv_lock_file_with_typo),
            use_cache=False,
            package_ecosystem="pypi",
        )

        assert mock_get_packages.call_count == 1
        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="reqests", similars=["requests"])]
        )

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    @patch("twyn.main._get_config")
    @patch("twyn.dependency_parser.parsers.abstract_parser.Path")
    def test_check_dependencies_detects_typosquats_and_autodetects_file(
        self,
        mock_fpath: Mock,
        mock_config: Mock,
        mock_get_packages: Mock,
        uv_lock_file_with_typo: Path,
    ) -> None:
        """Check that dependencies are loaded from file, retrieved from source, and a typosquat is detected."""
        mock_get_packages.return_value = {"requests"}
        mock_config.return_value = TwynConfiguration(
            str(uv_lock_file_with_typo),
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem=None,
        )
        mock_fpath.return_value = uv_lock_file_with_typo
        error = check_dependencies()

        assert mock_get_packages.call_count == 1
        assert mock_config.call_count == 1
        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="reqests", similars=["requests"])]
        )

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    @patch("twyn.main._get_config")
    @patch("twyn.dependency_parser.parsers.abstract_parser.Path")
    def test_check_dependencies_detects_typosquats_and_autodetects_file_and_language_is_set(
        self,
        mock_fpath: Mock,
        mock_config: Mock,
        mock_get_packages: Mock,
        uv_lock_file_with_typo: Path,
    ) -> None:
        """Check that dependencies are loaded from file, retrieved from source, and a typosquat is detected."""
        mock_get_packages.return_value = {"requests"}
        mock_config.return_value = TwynConfiguration(
            str(uv_lock_file_with_typo),
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem="pypi",
        )
        mock_fpath.return_value = uv_lock_file_with_typo
        error = check_dependencies()

        assert mock_get_packages.call_count == 1
        assert mock_config.call_count == 1
        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="reqests", similars=["requests"])]
        )

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_input_from_cli_detects_typosquats(
        self, mock_get_packages_from_cache: Mock
    ) -> None:
        mock_get_packages_from_cache.return_value = {"mypackage"}
        error = check_dependencies(
            dependencies={"my-package"},
            package_ecosystem="pypi",
        )

        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="my-package", similars=["mypackage"])]
        )

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_input_loads_file_from_different_location(
        self, mock_get_packages_from_cache: Mock, tmp_path: Path
    ) -> None:
        mock_get_packages_from_cache.return_value = {"mypackage"}
        tmp_file = tmp_path / "fake-dir" / "requirements.txt"
        with create_tmp_file(tmp_file, "mypackag"):
            error = check_dependencies(
                config_file=None,
                dependency_file=str(tmp_file),
                dependencies=None,
                selector_method="first-letter",
            )

        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="mypackag", similars=["mypackage"])]
        )

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_input_from_cli_accepts_multiple_dependencies(
        self, mock_get_packages_from_cache: Mock
    ) -> None:
        mock_get_packages_from_cache.return_value = {"requests", "mypackage"}

        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies={"my-package", "reqests"},
            selector_method="first-letter",
            package_ecosystem="pypi",
        )

        assert len(error.errors) == 2
        assert TyposquatCheckResult(dependency="reqests", similars=["requests"]) in error.errors
        assert TyposquatCheckResult(dependency="my-package", similars=["mypackage"]) in error.errors

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_ignores_package_in_allowlist(
        self, mock_get_packages: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        mock_get_packages.return_value = {"requests"}

        # Verify that before the whitelist configuration the package is classified as an error.
        error = check_dependencies(
            dependency_file=str(uv_lock_file_with_typo),
        )
        assert mock_get_packages.call_count == 1
        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="reqests", similars=["requests"])]
        )

        m_config = TwynConfiguration(
            allowlist={"reqests"},
            dependency_file=str(uv_lock_file_with_typo),
            selector_method="first-letter",
            use_cache=True,
            source=None,
            package_ecosystem=None,
        )

        # Check that the package is no longer an error
        with patch("twyn.main.ConfigHandler.resolve_config", return_value=m_config):
            error = check_dependencies(
                dependency_file=str(uv_lock_file_with_typo),
            )

        assert error == TyposquatCheckResultList(errors=[])

    @pytest.mark.parametrize(
        "package_name",
        [
            "my.package",
            "my-package",
            "my_package",
            "My.Package",
        ],
    )
    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_normalize_package(self, mock_get_packages_from_cache: Mock, package_name: Mock) -> None:
        mock_get_packages_from_cache.return_value = {"requests", "mypackage"}
        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies={package_name},
            selector_method="first-letter",
            package_ecosystem="pypi",
        )

        assert error == TyposquatCheckResultList(
            errors=[
                TyposquatCheckResult(dependency="my-package", similars=["mypackage"]),
            ]
        )

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_does_not_error_on_same_package(
        self, mock_get_packages: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        mock_get_packages.return_value = {"reqests"}  # According to the source, this package is correct

        error = check_dependencies(
            dependency_file=str(uv_lock_file_with_typo),
        )

        assert error == TyposquatCheckResultList(errors=[])

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    @patch("twyn.main._get_config")
    def test_track_is_disabled_by_default_when_used_as_package(
        self, mock_config: Mock, mock_get_packages: Mock, uv_lock_file: Path
    ) -> None:
        mock_config.return_value = TwynConfiguration(
            str(uv_lock_file),
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem=None,
        )
        mock_get_packages.return_value = {"requests"}
        with patch("twyn.main.track") as m_track:
            check_dependencies()
        assert m_track.call_count == 0

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    @patch("twyn.main._get_config")
    def test_track_is_shown_when_enabled(self, mock_config: Mock, mock_get_packages: Mock, uv_lock_file: Path) -> None:
        mock_config.return_value = TwynConfiguration(
            str(uv_lock_file),
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem=None,
        )
        mock_get_packages.return_value = {"requests"}
        with patch("twyn.main.track") as m_track:
            check_dependencies(show_progress_bar=True)
        assert m_track.call_count == 1

    def test_check_dependencies_invalid_arguments_error(self) -> None:
        """Test that InvalidArgumentsError is raised when dependencies are provided without package_ecosystem."""
        with pytest.raises(InvalidArgumentsError):
            check_dependencies(dependencies={"foo"}, package_ecosystem=None)

    def test_check_dependencies_invalid_language_error(self) -> None:
        """Test that InvalidArgumentsError is raised when a non valid package_ecosystem is given."""
        with pytest.raises(InvalidArgumentsError):
            check_dependencies(dependencies={"foo"}, package_ecosystem="asdf")

    def test_check_dependency_file_invalid_language_error(self) -> None:
        """Test that InvalidArgumentsError is raised when a non valid package_ecosystem is given together with a depdendecy_file."""
        with pytest.raises(InvalidArgumentsError):
            check_dependencies(dependency_file="uv.lock", package_ecosystem="asdf")

    def test_check_dependencies_invalid_selector_method_error(self) -> None:
        """Test that InvalidSelectorMethodError is raised when an invalid selector_method is provided."""
        with pytest.raises(InvalidSelectorMethodError):
            check_dependencies(selector_method="not-a-method", dependencies={"foo"}, package_ecosystem="pypi")

    def test_check_dependencies_npm_v3(self, package_lock_json_file_v3: Path) -> None:
        """Integration: check_dependencies works for npm v3 lockfile."""
        with patch_npm_packages_download(["expres"]) as m_download:
            result = check_dependencies(dependency_file=str(package_lock_json_file_v3), use_cache=False)
        found = {e.dependency for e in result.errors}
        assert m_download.call_count == 1
        assert found == {"express"}

    def test_get_top_reference_from_file_no_matching_parser_error(self) -> None:
        """Test that get_top_reference_from_file raises NoMatchingParserError for unknown file type."""
        with pytest.raises(NoMatchingDependencyManagerError):
            get_dependency_manager_from_file("unknown.lock")

    def test_get_top_reference_from_name_no_matching_parser_error(self) -> None:
        """Test that get_top_reference_from_name raises NoMatchingParserError for unknown language name."""
        with pytest.raises(NoMatchingDependencyManagerError):
            get_dependency_manager_from_name("unknownlang")

    def test_check_dependencies_yarn(self, yarn_lock_file_v1: Path) -> None:
        """Verifies that the yarn flow is working."""
        with patch_npm_packages_download(["lodas"]) as mock_download:
            result = check_dependencies(dependency_file=str(yarn_lock_file_v1), use_cache=False)
        found = {e.dependency for e in result.errors}

        assert mock_download.call_count == 1
        assert found == {"lodash"}
