from pathlib import Path
from typing import Any, Union
from unittest.mock import Mock, patch

import pytest
from tomlkit import dumps, parse
from twyn.base.constants import DEFAULT_TOP_PYPI_PACKAGES, AvailableLoggingLevels
from twyn.config.config_handler import ConfigHandler, TwynConfiguration, _get_logging_level
from twyn.dependency_parser import RequirementsTxtParser
from twyn.file_handler.file_handler import FileHandler
from twyn.main import (
    check_dependencies,
    get_parsed_dependencies_from_file,
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
                    "verbosity": AvailableLoggingLevels.info,
                },
                {
                    "logging_level": "WARNING",
                    "selector_method": "nearby-letter",
                    "dependency_file": "poetry.lock",
                    "allowlist": ["boto4", "boto2"],
                },
                TwynConfiguration(
                    dependency_file="requirements.txt",
                    selector_method="first-letter",
                    logging_level=AvailableLoggingLevels.info,
                    allowlist={"boto4", "boto2"},
                    pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
                    use_cache=True,
                ),
            ),
            (
                {
                    "verbosity": AvailableLoggingLevels.none,
                },
                {
                    "logging_level": "debug",
                    "selector_method": "nearby-letter",
                    "dependency_file": "poetry.lock",
                    "allowlist": ["boto4", "boto2"],
                },
                TwynConfiguration(
                    dependency_file="poetry.lock",
                    selector_method="nearby-letter",
                    logging_level=AvailableLoggingLevels.debug,
                    allowlist={"boto4", "boto2"},
                    pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
                    use_cache=True,
                ),
            ),
            (
                {
                    "verbosity": AvailableLoggingLevels.none,
                },
                {},
                TwynConfiguration(
                    dependency_file=None,
                    selector_method="all",
                    logging_level=AvailableLoggingLevels.warning,
                    allowlist=set(),
                    pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
                    use_cache=True,
                ),
            ),
            (
                {
                    "verbosity": AvailableLoggingLevels.debug,
                    "dependency_file": "requirements.txt",
                    "use_cache": False,
                },
                {
                    "logging_level": "INFO",
                    "dependency_file": "poetry.lock",
                    "allowlist": [],
                    "use_cache": False,
                },
                TwynConfiguration(
                    dependency_file="requirements.txt",
                    selector_method="all",
                    logging_level=AvailableLoggingLevels.debug,
                    allowlist=set(),
                    pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
                    use_cache=False,
                ),
            ),
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
        handler = ConfigHandler(FileHandler(""), enforce_file=False)

        with patch.object(handler, "_read_toml", return_value=parse(dumps({"tool": {"twyn": file_config}}))):
            resolved = handler.resolve_config(
                selector_method=cli_config.get("selector_method"),
                dependency_file=cli_config.get("dependency_file"),
                verbosity=cli_config.get("verbosity"),
                use_cache=cli_config.get("use_cache"),
            )

        assert resolved.dependency_file == expected_resolved_config.dependency_file
        assert resolved.selector_method == expected_resolved_config.selector_method
        assert resolved.logging_level == expected_resolved_config.logging_level
        assert resolved.allowlist == expected_resolved_config.allowlist
        assert resolved.use_cache == expected_resolved_config.use_cache

    @pytest.mark.parametrize(
        (
            "passed_logging_level",
            "config",
            "logging_level",
        ),
        [
            (AvailableLoggingLevels.none, None, AvailableLoggingLevels.warning),
            (AvailableLoggingLevels.info, None, AvailableLoggingLevels.info),
            (AvailableLoggingLevels.debug, None, AvailableLoggingLevels.debug),
            (AvailableLoggingLevels.none, "debug", AvailableLoggingLevels.debug),
        ],
    )
    def test_logging_level(
        self,
        passed_logging_level: AvailableLoggingLevels,
        config: Union[str, None],
        logging_level: AvailableLoggingLevels,
    ) -> None:
        log_level = _get_logging_level(
            cli_verbosity=passed_logging_level,
            config_logging_level=config,
        )
        assert log_level == logging_level

    @patch("twyn.main.get_parsed_dependencies_from_file")
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

    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main.get_parsed_dependencies_from_file")
    def test_check_dependencies_ignores_package_in_allowlist(
        self, mock_get_parsed_dependencies_from_file: Mock, mock_top_pypi_reference: Mock
    ) -> None:
        mock_top_pypi_reference.return_value.get_packages.return_value = {"mypackage"}
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
            logging_level=AvailableLoggingLevels.info,
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
    @patch("twyn.main.get_parsed_dependencies_from_file")
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
        assert get_parsed_dependencies_from_file() == {"boto3"}

    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main.get_parsed_dependencies_from_file")
    def test_track_is_disabled_by_default_when_used_as_package(
        self, mock_get_parsed_dependencies_from_file, mock_top_pypi_reference
    ) -> None:
        mock_top_pypi_reference.return_value.get_packages.return_value = {"mypackage"}
        mock_get_parsed_dependencies_from_file.return_value = {"my-package"}
        with patch("twyn.main.track") as m_track:
            check_dependencies()
        assert m_track.call_count == 0

    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main.get_parsed_dependencies_from_file")
    def test_track_is_shown_when_enabled(
        self, mock_get_parsed_dependencies_from_file: Mock, mock_top_pypi_reference: Mock
    ) -> None:
        mock_top_pypi_reference.return_value.get_packages.return_value = {"mypackage"}
        mock_get_parsed_dependencies_from_file.return_value = {"my-package"}
        with patch("twyn.main.track") as m_track:
            check_dependencies(use_track=True)
        assert m_track.call_count == 1
