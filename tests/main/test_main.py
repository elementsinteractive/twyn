import sys
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
from twyn.dependency_parser.dependency_selector import DependencySelector
from twyn.file_handler.file_handler import FileHandler
from twyn.main import (
    check_dependencies,
)
from twyn.trusted_packages import TopPyPiReference
from twyn.trusted_packages.exceptions import InvalidArgumentsError
from twyn.trusted_packages.models import (
    TyposquatCheckResultEntry,
    TyposquatCheckResultFromSource,
    TyposquatCheckResults,
)

from tests.conftest import create_tmp_file, patch_npm_packages_download


@pytest.mark.usefixtures("disable_track")
class TestCheckDependencies:
    @pytest.mark.parametrize(
        ("cli_config", "file_config", "expected_resolved_config"),
        [
            (
                {
                    "selector_method": "first-letter",
                    "dependency_file": {"requirements.txt"},
                    "use_cache": True,
                    "pypi_reference": "https://myurl.com",
                    "recurisve": True,
                },
                {
                    "selector_method": "nearby-letter",
                    "dependency_file": ["poetry.lock"],
                    "allowlist": ["boto4", "boto2"],  # There is no allowlist option in the cli
                    "use_cache": False,
                    "pypi_reference": "https://mysecondurl.com",
                    "recursive": False,
                },
                TwynConfiguration(
                    dependency_files={"requirements.txt"},
                    selector_method="first-letter",
                    allowlist={"boto4", "boto2"},
                    source=TopPyPiReference.DEFAULT_SOURCE,
                    use_cache=True,
                    package_ecosystem="pypi",
                    recursive=True,
                ),
            ),  # CLI args take precedence over config from file
            (
                {},
                {
                    "selector_method": "nearby-letter",
                    "dependency_file": ["poetry.lock"],
                    "allowlist": ["boto4", "boto2"],
                    "use_cache": False,
                    "pypi_reference": "https://mysecondurl.com",
                    "recursive": True,
                },
                TwynConfiguration(
                    dependency_files={"poetry.lock"},
                    selector_method="nearby-letter",
                    allowlist={"boto4", "boto2"},
                    source=TopPyPiReference.DEFAULT_SOURCE,
                    use_cache=False,
                    package_ecosystem="pypi",
                    recursive=True,
                ),
            ),  # Config from file takes precendence over fallback values
            (
                {},
                {},
                TwynConfiguration(
                    dependency_files=set(),
                    selector_method="all",
                    allowlist=set(),
                    source=TopPyPiReference.DEFAULT_SOURCE,
                    use_cache=True,
                    package_ecosystem="pypi",
                    recursive=False,
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
                dependency_files=cli_config.get("dependency_file", set()),
                use_cache=cli_config.get("use_cache"),
            )

        assert resolved.dependency_files == expected_resolved_config.dependency_files
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
            dependency_files={str(uv_lock_file_with_typo)},
            use_cache=False,
        )

        assert mock_get_packages.call_count == 1
        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                    source=str(uv_lock_file_with_typo),
                )
            ]
        )

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_detects_typosquats_from_file_and_language_is_set(
        self, mock_get_packages: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        """Check that dependencies are loaded from file, retrieved from source, and a typosquat is detected."""
        mock_get_packages.return_value = {"requests"}

        error = check_dependencies(
            dependency_files={str(uv_lock_file_with_typo)},
            use_cache=False,
            package_ecosystem="pypi",
        )

        assert mock_get_packages.call_count == 1
        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                    source=str(uv_lock_file_with_typo),
                )
            ]
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
            dependency_files={str(uv_lock_file_with_typo)},
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem=None,
            recursive=False,
        )
        mock_fpath.return_value = uv_lock_file_with_typo
        error = check_dependencies()

        assert mock_get_packages.call_count == 1
        assert mock_config.call_count == 1
        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                    source=str(uv_lock_file_with_typo),
                )
            ]
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
            dependency_files={str(uv_lock_file_with_typo)},
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem="pypi",
            recursive=False,
        )
        mock_fpath.return_value = uv_lock_file_with_typo
        error = check_dependencies()

        assert mock_get_packages.call_count == 1
        assert mock_config.call_count == 1
        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                    source=str(uv_lock_file_with_typo),
                )
            ]
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

        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="my-package", similars=["mypackage"])],
                    source="manual_input",
                )
            ]
        )

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_recursive_and_dependency_file_set(
        self, mock_get_packages_from_cache: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        """Test that recursive and dependency file can be set at the same time, and then dependency file takes precedence while recurisve is ignored."""
        mock_get_packages_from_cache.return_value = {"requests"}
        error = check_dependencies(
            dependency_files={str(uv_lock_file_with_typo)},
            package_ecosystem="pypi",
        )

        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                    source=str(uv_lock_file_with_typo),
                )
            ]
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
                dependency_files={str(tmp_file)},
                dependencies=None,
                selector_method="first-letter",
            )

        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="mypackag", similars=["mypackage"])],
                    source=str(tmp_file),
                )
            ]
        )

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_multiple_dependency_files(
        self, mock_get_packages_from_cache: Mock, tmp_path: Path, uv_lock_file_with_typo: Path
    ) -> None:
        mock_get_packages_from_cache.return_value = {"requests"}
        tmp_file = tmp_path / "fake-dir" / "requirements.txt"
        with create_tmp_file(tmp_file, "reqests"):
            error = check_dependencies(
                dependency_files={str(tmp_file), str(uv_lock_file_with_typo)},
            )

        assert (
            TyposquatCheckResultFromSource(
                errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                source=str(tmp_file),
            )
            in error.results
        )
        assert (
            TyposquatCheckResultFromSource(
                errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                source=str(uv_lock_file_with_typo),
            )
            in error.results
        )

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_input_from_cli_accepts_multiple_dependencies(
        self, mock_get_packages_from_cache: Mock
    ) -> None:
        mock_get_packages_from_cache.return_value = {"requests", "mypackage"}

        error = check_dependencies(
            config_file=None,
            dependency_files=None,
            dependencies={"my-package", "reqests"},
            selector_method="first-letter",
            package_ecosystem="pypi",
        )
        assert isinstance(error, TyposquatCheckResults)
        assert TyposquatCheckResultEntry(dependency="my-package", similars=["mypackage"]) in error.results[0]
        assert TyposquatCheckResultEntry(dependency="reqests", similars=["requests"]) in error.results[0]

    @patch("twyn.main._analyze_dependencies_from_input")
    @patch("twyn.main.ConfigHandler")
    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_loads_config_from_file(
        self, m_packages: Mock, mock_config: Mock, mock_analyze: Mock
    ) -> None:
        mock_analyze.return_value = TyposquatCheckResults()
        mock_config.return_value = ConfigHandler()
        m_packages.return_value = {"requests"}
        check_dependencies(load_config_from_file=True, use_cache=False, dependencies={"requests"})

        assert mock_config.call_count == 1
        assert len(mock_config.call_args) == 2
        assert len(mock_config.call_args[0]) == 1
        assert isinstance(mock_config.call_args[0][0], FileHandler)

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_input_from_cli_no_results(self, mock_get_packages_from_cache: Mock) -> None:
        mock_get_packages_from_cache.return_value = {"requests"}

        error = check_dependencies(
            config_file=None,
            dependency_files=None,
            dependencies={"requests"},
            selector_method="first-letter",
            package_ecosystem="pypi",
        )
        assert isinstance(error, TyposquatCheckResults)
        assert not error

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_error_when_show_progress_bar_and_dependencies_not_installed(
        self, mock_get_packages_from_cache: Mock
    ) -> None:
        mock_get_packages_from_cache.return_value = {"requests"}
        sys.modules.pop("rich.progress", None)
        sys.modules.pop("rich", None)

        with patch.dict(sys.modules, {"rich.progress": None}), pytest.raises(InvalidArgumentsError):
            check_dependencies(
                dependencies={"requests"},
                selector_method="first-letter",
                package_ecosystem="pypi",
                show_progress_bar=True,
            )

    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    @patch("twyn.main.InvalidArgumentsError")
    def test_no_error_when_no_show_progress_bar_and_dependencies_not_installed(
        self, mock_exc: Mock, mock_get_packages_from_cache: Mock
    ) -> None:
        mock_exc.side_effect = Exception()

        mock_get_packages_from_cache.return_value = {"requests"}
        sys.modules.pop("rich.progress", None)
        sys.modules.pop("rich", None)

        with patch.dict(sys.modules, {"rich.progress": None}):
            result = check_dependencies(
                dependencies={"requests"},
                selector_method="first-letter",
                package_ecosystem="pypi",
                show_progress_bar=False,
            )
        assert not result
        assert mock_exc.call_count == 0

    def test_get_invalid_selector_method(self) -> None:
        with pytest.raises(InvalidSelectorMethodError):
            check_dependencies(selector_method="i am batman")

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_ignores_package_in_allowlist(
        self, mock_get_packages: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        mock_get_packages.return_value = {"requests"}

        # Verify that before the whitelist configuration the package is classified as an error.
        error = check_dependencies(
            dependency_files={str(uv_lock_file_with_typo)},
        )
        assert mock_get_packages.call_count == 1
        assert error == TyposquatCheckResults(
            results=[
                TyposquatCheckResultFromSource(
                    errors=[TyposquatCheckResultEntry(dependency="reqests", similars=["requests"])],
                    source=str(uv_lock_file_with_typo),
                )
            ]
        )

        m_config = TwynConfiguration(
            allowlist={"reqests"},
            dependency_files={str(uv_lock_file_with_typo)},
            selector_method="first-letter",
            use_cache=True,
            source=None,
            package_ecosystem=None,
            recursive=False,
        )

        # Check that the package is no longer an error
        with patch("twyn.main.ConfigHandler.resolve_config", return_value=m_config):
            error = check_dependencies(
                dependency_files={str(uv_lock_file_with_typo)},
            )

        assert error == TyposquatCheckResults(results=[])

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependencies_does_not_error_on_same_package(
        self, mock_get_packages: Mock, uv_lock_file_with_typo: Path
    ) -> None:
        mock_get_packages.return_value = {"reqests"}  # According to the source, this package is correct

        error = check_dependencies(
            dependency_files={str(uv_lock_file_with_typo)},
        )

        assert error == TyposquatCheckResults(results=[])

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    @patch("twyn.main._get_config")
    def test_track_is_disabled_by_default_when_used_as_package(
        self, mock_config: Mock, mock_get_packages: Mock, uv_lock_file: Path
    ) -> None:
        mock_config.return_value = TwynConfiguration(
            dependency_files={str(uv_lock_file)},
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem=None,
            recursive=False,
        )
        mock_get_packages.return_value = {"requests"}
        with patch("rich.progress.track") as m_track:
            check_dependencies()
        assert m_track.call_count == 0

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    @patch("twyn.main._get_config")
    def test_track_is_shown_when_enabled(self, mock_config: Mock, mock_get_packages: Mock, uv_lock_file: Path) -> None:
        mock_config.return_value = TwynConfiguration(
            dependency_files={str(uv_lock_file)},
            selector_method="all",
            allowlist=set(),
            source=None,
            use_cache=False,
            package_ecosystem=None,
            recursive=False,
        )
        mock_get_packages.return_value = {"requests"}
        with patch("rich.progress.track") as m_track:
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

    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_check_dependency_file_invalid_language_error(self, m_packages: Mock, uv_lock_file_with_typo: Path) -> None:
        """Test that when a non valid package_ecosystem is given together with a depdendecy_file, package_ecosystem is ignored."""
        m_packages.return_value = {"requests"}
        result = check_dependencies(
            dependency_files={str(uv_lock_file_with_typo)}, package_ecosystem="npm", use_cache=False
        )
        assert bool(result)

    def test_check_dependencies_invalid_selector_method_error(self) -> None:
        """Test that InvalidSelectorMethodError is raised when an invalid selector_method is provided."""
        with pytest.raises(InvalidSelectorMethodError):
            check_dependencies(selector_method="not-a-method", dependencies={"foo"}, package_ecosystem="pypi")

    def test_check_dependencies_npm_v3(self, package_lock_json_file_v3: Path) -> None:
        """Integration: check_dependencies works for npm v3 lockfile."""
        with patch_npm_packages_download(["expres"]) as m_download:
            result = check_dependencies(dependency_files={str(package_lock_json_file_v3)}, use_cache=False)

        assert m_download.call_count == 1
        assert len(result.results) == 1  # only one file was scanned
        assert result.results == [
            TyposquatCheckResultFromSource(
                errors=[TyposquatCheckResultEntry(dependency="express", similars=["expres"])],
                source=str(package_lock_json_file_v3),
            )
        ]

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
            result = check_dependencies(dependency_files={str(yarn_lock_file_v1)}, use_cache=False)

        assert mock_download.call_count == 1
        assert len(result.results) == 1  # only one file was scanned
        assert result.results == [
            TyposquatCheckResultFromSource(
                errors=[TyposquatCheckResultEntry(dependency="lodash", similars=["lodas"])],
                source=str(yarn_lock_file_v1),
            )
        ]

    @patch("twyn.main.DependencySelector")
    @patch("twyn.trusted_packages.TopPyPiReference.get_packages")
    def test_auto_detect_dependency_file_parser_scans_subdirectories(
        self, m_packages: Mock, m_dep_selector: Mock, tmp_path: Path
    ) -> None:
        # Create nested directories and dependency files
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        req_file = subdir / "requirements.txt"
        req_file.write_text("reqests\n")

        m_dep_selector.return_value = DependencySelector(root_path=str(tmp_path))
        m_packages.return_value = {"requests"}

        error = check_dependencies(recursive=True, use_cache=False)

        assert len(error.results) == 1
        assert error.get_results_from_source(str(req_file)) is not None
