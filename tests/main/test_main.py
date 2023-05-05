from unittest.mock import Mock, call, patch

import pytest
from twyn.base.constants import AvailableLoggingLevels
from twyn.dependency_parser import RequirementsTxtParser
from twyn.main import (
    check_dependencies,
    get_configuration,
    get_logging_level,
    get_parsed_dependencies,
)


@pytest.mark.usefixtures("disable_track")
class TestCheckDependencies:
    @pytest.mark.parametrize(
        "selector_method, dependency_file, verbosity, config, expected_args, log_level",
        [
            (
                "requirements.txt",
                "first-letter",
                AvailableLoggingLevels.info,
                {
                    "logging_level": "WARNING",
                    "selector_method": "nearby-letter",
                    "dependency_file": "poetry.lock",
                    "allowlist": {"boto4", "boto2"},
                },
                ["first-letter", "requirements.txt", {"boto4", "boto2"}],
                AvailableLoggingLevels.info,
            ),
            (
                None,
                None,
                AvailableLoggingLevels.none,
                {
                    "logging_level": "debug",
                    "selector_method": "nearby-letter",
                    "dependency_file": "poetry.lock",
                    "allowlist": {"boto4", "boto2"},
                },
                ["poetry.lock", "nearby-letter", {"boto4", "boto2"}],
                AvailableLoggingLevels.debug,
            ),
            (
                None,
                None,
                AvailableLoggingLevels.none,
                {
                    "logging_level": None,
                    "selector_method": None,
                    "dependency_file": None,
                    "allowlist": set(),
                },
                [None, "all", set()],
                AvailableLoggingLevels.warning,
            ),
            (
                None,
                "requirements.txt",
                AvailableLoggingLevels.debug,
                {
                    "logging_level": "INFO",
                    "selector_method": None,
                    "dependency_file": "poetry.lock",
                    "allowlist": set(),
                },
                ["requirements.txt", "all", set()],
                AvailableLoggingLevels.debug,
            ),
        ],
    )
    @patch("twyn.main.set_logging_level")
    def test_options_priorities_assignation(
        self,
        mock_logging_level,
        selector_method,
        dependency_file,
        verbosity,
        config,
        expected_args,
        log_level,
    ):
        """
        Checks that the configuration values are picked accordingly to the priority they have.

        From more relevant to less:
        1. command line
        2. config file
        3. default values

        """
        with patch("twyn.main.ConfigHandler", return_value=Mock(**config)):
            config = get_configuration(
                dependency_file=dependency_file,
                config_file=None,
                selector_method=selector_method,
                verbosity=verbosity,
            )
        assert config.dependency_file == expected_args[0]
        assert config.selector_method == expected_args[1]
        assert config.allowlist == expected_args[2]

        assert mock_logging_level.call_args == call(log_level)

    @pytest.mark.parametrize(
        "passed_logging_level, config, logging_level",
        [
            [AvailableLoggingLevels.none, None, AvailableLoggingLevels.warning],
            [AvailableLoggingLevels.info, None, AvailableLoggingLevels.info],
            [AvailableLoggingLevels.debug, None, AvailableLoggingLevels.debug],
            [AvailableLoggingLevels.none, "debug", AvailableLoggingLevels.debug],
        ],
    )
    def test_logging_level(self, passed_logging_level, config, logging_level):
        log_level = get_logging_level(
            logging_level=passed_logging_level,
            config_logging_level=config,
        )
        assert log_level == logging_level

    @pytest.mark.parametrize(
        "package_name",
        (
            "my.package",
            "my-package",
            "my_package",
            "My.Package",
        ),
    )
    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main.get_parsed_dependencies")
    def test_check_dependencies_detects_typosquats(
        self, mock_get_parsed_dependencies, mock_top_pypi_reference, package_name
    ):
        mock_top_pypi_reference.return_value.get_packages.return_value = {"mypackage"}
        mock_get_parsed_dependencies.return_value = {package_name}

        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            selector_method="first-letter",
        )

        assert error is True

    @pytest.mark.parametrize(
        "package_name",
        (
            "my.package",
            "my-package",
            "my_package",
            "My.Package",
        ),
    )
    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main.get_parsed_dependencies")
    def test_check_dependencies_ignores_package_in_allowlist(
        self, mock_get_parsed_dependencies, mock_top_pypi_reference, package_name
    ):
        mock_top_pypi_reference.return_value.get_packages.return_value = {"mypackage"}
        mock_get_parsed_dependencies.return_value = {package_name}

        m_config = Mock(
            allowlist={package_name},
            dependency_file=None,
            selector_method="first-letter",
        )

        with patch("twyn.main.get_configuration", return_value=m_config):
            error = check_dependencies(
                config_file=None,
                dependency_file=None,
                selector_method="first-letter",
            )

        assert error is False

    @pytest.mark.parametrize(
        "package_name", ("my.package", "my-package", "my_package", "My.Package")
    )
    @patch("twyn.main.TopPyPiReference")
    @patch("twyn.main.get_parsed_dependencies")
    def test_check_dependencies_does_not_error_on_same_package(
        self, mock_get_parsed_dependencies, mock_top_pypi_reference, package_name
    ):
        mock_top_pypi_reference.return_value.get_packages.return_value = {"my-package"}
        mock_get_parsed_dependencies.return_value = {package_name}

        error = check_dependencies(
            config_file=None,
            dependency_file=None,
            selector_method="first-letter",
        )

        assert error is False

    @patch(
        "twyn.dependency_parser.dependency_selector.DependencySelector.get_dependency_parser"
    )
    @patch("twyn.dependency_parser.requirements_txt.RequirementsTxtParser.parse")
    def test_get_parsed_dependencies(self, mock_parse, mock_get_dependency_parser):
        mock_get_dependency_parser.return_value = RequirementsTxtParser()
        mock_parse.return_value = {"boto3"}
        assert get_parsed_dependencies() == {"boto3"}
