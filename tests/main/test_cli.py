from unittest.mock import call, patch

from click.testing import CliRunner
from twyn import cli
from twyn.base.constants import AvailableLoggingLevels
from twyn.trusted_packages.trusted_packages import TyposquatCheckResult


class TestCli:
    @patch("twyn.config.config_handler.ConfigHandler.add_package_to_allowlist")
    def test_allowlist_add_package_to_allowlist(self, mock_allowlist_add):
        runner = CliRunner()
        runner.invoke(
            cli.add,
            ["requests"],
        )

        assert mock_allowlist_add.call_args == call("requests")

    @patch("twyn.config.config_handler.ConfigHandler.remove_package_from_allowlist")
    def test_allowlist_remove(self, mock_allowlist_add):
        runner = CliRunner()
        runner.invoke(
            cli.remove,
            ["requests"],
        )

        assert mock_allowlist_add.call_args == call("requests")

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_dependency_file(self, mock_check_dependencies):
        runner = CliRunner()
        runner.invoke(
            cli.run,
            [
                "--config",
                "my-config",
                "--selector-method",
                "first-letter",
                "--dependency-file",
                "requirements.txt",
                "-vv",
            ],
        )

        assert mock_check_dependencies.call_args_list == [
            call(
                config_file="my-config",
                dependency_file="requirements.txt",
                dependencies=None,
                selector_method="first-letter",
                verbosity=AvailableLoggingLevels.debug,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_dependency_file_in_different_path(self, mock_check_dependencies):
        runner = CliRunner()
        runner.invoke(
            cli.run,
            [
                "--dependency-file",
                "/path/requirements.txt",
            ],
        )

        assert mock_check_dependencies.call_args_list == [
            call(
                config_file=None,
                dependency_file="/path/requirements.txt",
                dependencies=None,
                selector_method=None,
                verbosity=AvailableLoggingLevels.none,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_single_dependency_cli(self, mock_check_dependencies):
        runner = CliRunner()
        runner.invoke(
            cli.run,
            [
                "--dependency",
                "reqests",
            ],
        )
        assert mock_check_dependencies.call_args_list == [
            call(
                config_file=None,
                dependency_file=None,
                dependencies={"reqests"},
                selector_method=None,
                verbosity=AvailableLoggingLevels.none,
            )
        ]

    def test_click_raises_error_dependency_and_dependency_file_set(self):
        runner = CliRunner()
        result = runner.invoke(
            cli.run, ["--dependency", "requests", "--dependency-file", "requirements.txt"], catch_exceptions=False
        )
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
        assert "Only one of --dependency or --dependency-file can be set at a time." in result.output

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_multiple_dependencies(self, mock_check_dependencies):
        runner = CliRunner()
        runner.invoke(
            cli.run,
            [
                "--dependency",
                "reqests",
                "--dependency",
                "reqeusts",
            ],
        )

        assert mock_check_dependencies.call_args_list == [
            call(
                config_file=None,
                dependency_file=None,
                dependencies={"reqests", "reqeusts"},
                selector_method=None,
                verbosity=AvailableLoggingLevels.none,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_default(self, mock_check_dependencies):
        runner = CliRunner()
        runner.invoke(cli.run)

        assert mock_check_dependencies.call_args_list == [
            call(
                config_file=None,
                dependency_file=None,
                selector_method=None,
                dependencies=None,
                verbosity=AvailableLoggingLevels.none,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_return_code_1(self, mock_check_dependencies):
        runner = CliRunner()
        mock_check_dependencies.return_value = [
            TyposquatCheckResult(candidate_dependency="my-package", similar_dependencies=["mypackage"])
        ]

        result = runner.invoke(cli.run)
        assert result.exit_code == 1

    @patch("twyn.cli.check_dependencies")
    def test_return_code_0(self, mock_check_dependencies):
        runner = CliRunner()
        mock_check_dependencies.return_value = []

        result = runner.invoke(cli.run)
        assert result.exit_code == 0

    def test_only_one_verbosity_level_is_allowed(self):
        runner = CliRunner()
        result = runner.invoke(cli.run, ["-v", "-vv"], catch_exceptions=False)

        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
        assert "Only one verbosity level is allowed. Choose either -v or -vv." in result.output

    def test_dependency_file_name_has_to_be_recognized(self):
        runner = CliRunner()
        result = runner.invoke(cli.run, ["--dependency-file", "requirements-dev.txt"], catch_exceptions=False)

        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
        assert "Dependency file name not supported." in result.output
