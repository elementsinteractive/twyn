from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from click.testing import CliRunner
from twyn import cli
from twyn.base.constants import AvailableLoggingLevels
from twyn.base.exceptions import TwynError
from twyn.trusted_packages.cache_handler import CacheEntry, CacheHandler
from twyn.trusted_packages.trusted_packages import TyposquatCheckResult, TyposquatCheckResultList


class TestCli:
    def test_cache_clear_removes_all_cache_files(self, tmp_path: Path) -> None:
        """Test that cache clear without source removes all cache files."""
        # Create some cache files for different sources
        cache_handler = CacheHandler(tmp_path)
        sources = ["https://pypi.org/simple/", "https://registry.npmjs.org/", "https://example.com/packages/"]

        for source in sources:
            entry = CacheEntry(saved_date="2025-01-01", packages={"package1", "package2"})
            cache_handler.write_entry(source, entry)

        # Verify cache files exist
        cache_files = list(tmp_path.glob("*.json"))

        assert len(cache_files) == 3

        runner = CliRunner()
        with patch("twyn.cli.CACHE_DIR", tmp_path):
            result = runner.invoke(cli.cache.commands["clear"])

        assert result.exit_code == 0

        # Verify all cache files are removed
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 0

    @patch("twyn.cli.check_dependencies")
    def test_no_cache_option_disables_cache(self, mock_check_dependencies: Mock) -> None:
        runner = CliRunner()
        runner.invoke(
            cli.run,
            ["--no-cache", "--dependency", "requests"],
        )
        assert mock_check_dependencies.call_args[1]["use_cache"] is False
        assert mock_check_dependencies.call_args[1]["dependencies"] == {"requests"}

    @patch("twyn.config.config_handler.ConfigHandler.add_package_to_allowlist")
    def test_allowlist_add_package_to_allowlist(self, mock_allowlist_add: Mock) -> None:
        runner = CliRunner()
        runner.invoke(
            cli.add,
            ["requests"],
        )

        assert mock_allowlist_add.call_args == call("requests")

    @patch("twyn.config.config_handler.ConfigHandler.remove_package_from_allowlist")
    def test_allowlist_remove(self, mock_allowlist_add: Mock) -> None:
        runner = CliRunner()
        runner.invoke(
            cli.remove,
            ["requests"],
        )

        assert mock_allowlist_add.call_args == call("requests")

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_dependency_file(self, mock_check_dependencies: Mock) -> None:
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
                use_cache=None,
                use_track=True,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_dependency_file_in_different_path(self, mock_check_dependencies: Mock) -> None:
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
                use_cache=None,
                use_track=True,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_single_dependency_cli(self, mock_check_dependencies: Mock) -> None:
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
                use_cache=None,
                use_track=True,
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
    def test_click_arguments_multiple_dependencies(self, mock_check_dependencies: Mock) -> None:
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
                use_cache=None,
                use_track=True,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_click_arguments_default(self, mock_check_dependencies: Mock) -> None:
        runner = CliRunner()
        runner.invoke(cli.run)

        assert mock_check_dependencies.call_args_list == [
            call(
                config_file=None,
                dependency_file=None,
                selector_method=None,
                dependencies=None,
                verbosity=AvailableLoggingLevels.none,
                use_cache=None,
                use_track=True,
            )
        ]

    @patch("twyn.cli.check_dependencies")
    def test_return_code_1(self, mock_check_dependencies: Mock) -> None:
        runner = CliRunner()
        mock_check_dependencies.return_value = TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="my-package", similars=["mypackage"])]
        )

        result = runner.invoke(cli.run)
        assert result.exit_code == 1
        assert "did you mean any of [mypackage]" in result.output

    @patch("twyn.cli.check_dependencies")
    def test_json_typo_detected(self, mock_check_dependencies: Mock) -> None:
        mock_check_dependencies.return_value = TyposquatCheckResultList(
            errors=[TyposquatCheckResult(dependency="my-package", similars=["mypackage"])]
        )
        runner = CliRunner()
        result = runner.invoke(
            cli.run,
            [
                "--json",
            ],
        )

        assert result.exit_code == 1
        assert result.output == '{"errors":[{"dependency":"my-package","similars":["mypackage"]}]}\n'

    @patch("twyn.cli.check_dependencies")
    def test_json_no_typo(self, mock_check_dependencies: Mock) -> None:
        mock_check_dependencies.return_value = TyposquatCheckResultList(errors=[])
        runner = CliRunner()
        result = runner.invoke(
            cli.run,
            [
                "--json",
            ],
        )

        assert result.exit_code == 0
        assert result.output == '{"errors":[]}\n'

    @patch("twyn.cli.check_dependencies")
    def test_return_code_0(self, mock_check_dependencies: Mock) -> None:
        runner = CliRunner()
        mock_check_dependencies.return_value = TyposquatCheckResultList()

        result = runner.invoke(cli.run)

        assert result.exit_code == 0
        assert "No typosquats detected" in result.output

    def test_dependency_file_name_has_to_be_recognized(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.run, ["--dependency-file", "requirements-dev.txt"], catch_exceptions=False)

        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
        assert "Dependency file name not supported." in result.output

    @patch("twyn.cli.check_dependencies")
    def test_base_twyn_error_is_caught_and_wrapped_in_cli_error(self, mock_check_dependencies, caplog):
        """Test that BaseTwynError is caught and wrapped in CliError."""
        runner = CliRunner()

        # Mock check_dependencies to raise a BaseTwynError
        test_error = TwynError("Test base error")
        test_error.message = "Test base error message"
        mock_check_dependencies.side_effect = test_error

        result = runner.invoke(cli.run, ["--dependency", "requests"])

        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        # Check that the error message was logged
        assert "Test base error message" in caplog.text

    @patch("twyn.cli.check_dependencies")
    def test_unhandled_exception_is_caught_and_wrapped_in_cli_error(
        self, mock_check_dependencies: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that unhandled exceptions are caught and wrapped in CliError."""
        runner = CliRunner()

        # Mock check_dependencies to raise a generic exception
        mock_check_dependencies.side_effect = ValueError("Unexpected error")

        result = runner.invoke(cli.run, ["--dependency", "requests"])

        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        # Check that the generic error message was logged
        assert "Unhandled exception occured." in caplog.text
