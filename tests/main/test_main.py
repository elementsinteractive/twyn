from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from tomlkit import dumps, parse
from twyn.base.constants import DEFAULT_TOP_PYPI_PACKAGES
from twyn.config.config_handler import ConfigHandler, TwynConfiguration
from twyn.dependency_parser import RequirementsTxtParser
from twyn.file_handler.file_handler import FileHandler
from twyn.main import (
    _get_parsed_dependencies_from_file,
    check_dependencies,
)
from twyn.trusted_packages.trusted_packages import TyposquatCheckResult, TyposquatCheckResultList

from tests.conftest import create_tmp_file


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
                    pypi_reference="https://myurl.com",
                    use_cache=True,
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
                    pypi_reference="https://mysecondurl.com",
                    use_cache=False,
                ),
            ),  # Config from file takes precendence over fallback values
            (
                {},
                {},
                TwynConfiguration(
                    dependency_file=None,
                    selector_method="all",
                    allowlist=set(),
                    pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
                    use_cache=True,
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

    @patch("twyn.main._get_parsed_dependencies_from_file")
    @patch("twyn.trusted_packages.references.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_detects_typosquats(
        self, mock_get_packages_from_cache: Mock, mock_get_parsed_dependencies_from_file: Mock
    ) -> None:
        mock_get_parsed_dependencies_from_file.return_value = {"my-package"}
        mock_get_packages_from_cache.return_value = {"mypackage"}
        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies=None,
            selector_method="first-letter",
        )

        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="my-package", similars=["mypackage"])]
        )

    @patch("twyn.trusted_packages.references.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_input_from_cli_detects_typosquats(
        self, mock_get_packages_from_cache: Mock
    ) -> None:
        mock_get_packages_from_cache.return_value = {"mypackage"}
        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies={"my-package"},
            selector_method="first-letter",
        )

        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="my-package", similars=["mypackage"])]
        )

    @patch("twyn.trusted_packages.references.TopPyPiReference._get_packages_from_cache_if_enabled")
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

    @patch("twyn.trusted_packages.references.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_with_input_from_cli_accepts_multiple_dependencies(
        self, mock_get_packages_from_cache: Mock
    ) -> None:
        mock_get_packages_from_cache.return_value = {"requests", "mypackage"}

        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies={"my-package", "reqests"},
            selector_method="first-letter",
        )

        assert len(error.errors) == 2
        assert TyposquatCheckResult(dependency="reqests", similars=["requests"]) in error.errors
        assert TyposquatCheckResult(dependency="my-package", similars=["mypackage"]) in error.errors

    @patch("twyn.main.TopPyPiReference.get_packages")
    @patch("twyn.main._get_parsed_dependencies_from_file")
    def test_check_dependencies_ignores_package_in_allowlist(
        self, mock_get_parsed_dependencies_from_file: Mock, mock_get_packages: Mock
    ) -> None:
        mock_get_packages.return_value = {"mypackage"}
        mock_get_parsed_dependencies_from_file.return_value = {"my-package"}

        # Verify that before the whitelist configuration the package is classified as an error.
        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies=None,
            selector_method="first-letter",
        )

        assert error == TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="my-package", similars=["mypackage"])]
        )

        m_config = TwynConfiguration(
            allowlist={"my-package"},
            dependency_file=None,
            selector_method="first-letter",
            pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
            use_cache=True,
        )

        # Check that the package is no longer an error
        with patch("twyn.main.ConfigHandler.resolve_config", return_value=m_config):
            error = check_dependencies(
                config_file=None,
                dependency_file=None,
                dependencies=None,
                selector_method="first-letter",
                use_cache=True,
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
    @patch("twyn.trusted_packages.references.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_normalize_package(self, mock_get_packages_from_cache: Mock, package_name: Mock) -> None:
        mock_get_packages_from_cache.return_value = {"requests", "mypackage"}
        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies={package_name},
            selector_method="first-letter",
        )

        assert error == TyposquatCheckResultList(
            errors=[
                TyposquatCheckResult(dependency="my-package", similars=["mypackage"]),
            ]
        )

    @pytest.mark.parametrize("package_name", ["my.package", "my-package", "my_package", "My.Package"])
    @patch("twyn.main._get_parsed_dependencies_from_file")
    @patch("twyn.trusted_packages.references.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_check_dependencies_does_not_error_on_same_package(
        self, mock_get_packages_from_cache: Mock, mock_get_parsed_dependencies_from_file: Mock, package_name: Mock
    ) -> None:
        mock_get_parsed_dependencies_from_file.return_value = {package_name}
        mock_get_packages_from_cache.return_value = {"my-package"}
        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            dependencies=None,
            selector_method="first-letter",
        )

        assert error == TyposquatCheckResultList(errors=[])

    @patch("twyn.dependency_parser.dependency_selector.DependencySelector.get_dependency_parser")
    @patch("twyn.dependency_parser.requirements_txt_parser.RequirementsTxtParser.parse")
    def test_get_parsed_dependencies_from_file(self, mock_parse: Mock, mock_get_dependency_parser: Mock) -> None:
        mock_get_dependency_parser.return_value = RequirementsTxtParser()
        mock_parse.return_value = {"boto3"}
        assert _get_parsed_dependencies_from_file() == {"boto3"}

    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main._get_parsed_dependencies_from_file")
    def test_track_is_disabled_by_default_when_used_as_package(
        self, mock_get_parsed_dependencies_from_file, mock_top_pypi_reference
    ) -> None:
        mock_top_pypi_reference.return_value.get_packages.return_value = {"mypackage"}
        mock_get_parsed_dependencies_from_file.return_value = {"my-package"}
        with patch("twyn.main.track") as m_track:
            check_dependencies()
        assert m_track.call_count == 0

    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main._get_parsed_dependencies_from_file")
    def test_track_is_shown_when_enabled(
        self, mock_get_parsed_dependencies_from_file: Mock, mock_top_pypi_reference: Mock
    ) -> None:
        mock_top_pypi_reference.return_value.get_packages.return_value = {"mypackage"}
        mock_get_parsed_dependencies_from_file.return_value = {"my-package"}
        with patch("twyn.main.track") as m_track:
            check_dependencies(show_progress_bar=True)
        assert m_track.call_count == 1
