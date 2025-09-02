import dataclasses
from copy import deepcopy
from pathlib import Path
from typing import NoReturn
from unittest.mock import Mock, patch

import pytest
from tomlkit import TOMLDocument, dumps, parse
from twyn.base.constants import (
    DEFAULT_PROJECT_TOML_FILE,
    DEFAULT_TOP_PYPI_PACKAGES,
    DEFAULT_TWYN_TOML_FILE,
    AvailableLoggingLevels,
)
from twyn.config.config_handler import ConfigHandler, ReadTwynConfiguration, TwynConfiguration
from twyn.config.exceptions import (
    AllowlistPackageAlreadyExistsError,
    AllowlistPackageDoesNotExistError,
    InvalidSelectorMethodError,
    TOMLError,
)
from twyn.file_handler.exceptions import PathNotFoundError
from twyn.file_handler.file_handler import FileHandler

from tests.conftest import create_tmp_file


class TestConfigHandler:
    def throw_exception(self) -> NoReturn:
        raise PathNotFoundError

    @patch("twyn.file_handler.file_handler.FileHandler.read")
    def test_enforce_file_error(self, mock_is_file: Mock) -> None:
        mock_is_file.side_effect = self.throw_exception
        with pytest.raises(TOMLError):
            ConfigHandler(FileHandler(DEFAULT_PROJECT_TOML_FILE), enforce_file=True).resolve_config()

    @patch("twyn.file_handler.file_handler.FileHandler.read")
    def test_no_enforce_file_on_non_existent_file(self, mock_is_file: Mock) -> None:
        """Resolving the config without enforcing the file to be present gives you defaults."""
        mock_is_file.side_effect = self.throw_exception
        config = ConfigHandler(FileHandler(DEFAULT_PROJECT_TOML_FILE), enforce_file=False).resolve_config()

        assert config == TwynConfiguration(
            dependency_file=None,
            selector_method="all",
            logging_level=AvailableLoggingLevels.warning,
            allowlist=set(),
            pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
        )

    def test_config_raises_for_unknown_file(self) -> None:
        with pytest.raises(TOMLError):
            ConfigHandler(FileHandler("non-existent-file.toml")).resolve_config()

    def test_read_config_values(self, pyproject_toml_file: Path) -> None:
        config = ConfigHandler(file_handler=FileHandler(pyproject_toml_file)).resolve_config()
        assert config.dependency_file == "my_file.txt"
        assert config.selector_method == "all"
        assert config.logging_level == AvailableLoggingLevels.debug
        assert config.allowlist == {"boto4", "boto2"}

    def test_get_twyn_data_from_file(self, pyproject_toml_file: Path) -> None:
        handler = ConfigHandler(FileHandler(str(pyproject_toml_file)))

        toml = handler._read_toml()
        twyn_data = ConfigHandler(FileHandler(pyproject_toml_file))._get_read_config(toml)
        assert twyn_data == ReadTwynConfiguration(
            dependency_file="my_file.txt",
            selector_method="all",
            logging_level="debug",
            allowlist={"boto4", "boto2"},
            pypi_reference=None,
        )

    def test_write_toml(self, pyproject_toml_file: Path) -> None:
        handler = ConfigHandler(FileHandler(pyproject_toml_file))
        toml = handler._read_toml()

        initial_config = handler.resolve_config()
        to_write = deepcopy(initial_config)
        to_write = dataclasses.replace(to_write, allowlist={})

        handler._write_config(toml, to_write)

        new_config = handler.resolve_config()

        assert new_config != initial_config
        assert new_config.allowlist == set()
        # Writing the config should result in changes in the twyn section but
        # nowhere else
        assert handler._read_toml() == {
            "tool": {
                "poetry": {
                    "dependencies": {
                        "python": "^3.11",
                        "requests": "^2.28.2",
                        "dparse": "^0.6.2",
                        "click": "^8.1.3",
                        "rich": "^13.3.1",
                        "rapidfuzz": "^2.13.7",
                        "regex": "^2022.10.31",
                    },
                    "scripts": {"twyn": "twyn.cli:entry_point"},
                },
                "twyn": {
                    "dependency_file": "my_file.txt",
                    "selector_method": "all",
                    "logging_level": "debug",
                    "allowlist": {},
                    "pypi_reference": DEFAULT_TOP_PYPI_PACKAGES,
                },
            }
        }

    def test_get_default_config_file_path_twyn_file_exists(self, tmp_path: Path, pyproject_toml_file: Path) -> None:
        assert pyproject_toml_file.exists()
        twyn_path = tmp_path / DEFAULT_TWYN_TOML_FILE
        with (
            create_tmp_file(twyn_path, ""),
            patch("twyn.config.config_handler.DEFAULT_TWYN_TOML_FILE", new=str(twyn_path)),
            patch("twyn.config.config_handler.DEFAULT_PROJECT_TOML_FILE", new=str(pyproject_toml_file)),
        ):
            assert twyn_path.exists()

            assert ConfigHandler.get_default_config_file_path() == str(twyn_path)

    def test_get_default_config_file_path_twyn_file_does_not_exist(
        self, tmp_path: Path, pyproject_toml_file: Path
    ) -> None:
        assert pyproject_toml_file.exists()
        twyn_path = tmp_path / DEFAULT_TWYN_TOML_FILE
        with (
            patch("twyn.config.config_handler.DEFAULT_TWYN_TOML_FILE", new=str(twyn_path)),
            patch("twyn.config.config_handler.DEFAULT_PROJECT_TOML_FILE", new=str(pyproject_toml_file)),
        ):
            assert not twyn_path.exists()
            assert ConfigHandler.get_default_config_file_path() == str(pyproject_toml_file)


class TestAllowlistConfigHandler:
    @patch("twyn.file_handler.file_handler.FileHandler.write")
    @patch("twyn.config.config_handler.ConfigHandler._read_toml")
    def test_allowlist_add(self, mock_toml: Mock, mock_write_toml: Mock) -> None:
        mock_toml.return_value = TOMLDocument()

        config = ConfigHandler(FileHandler("some-file"))

        config.add_package_to_allowlist("mypackage")

        final_toml = config._read_toml()

        assert final_toml == {"tool": {"twyn": {"allowlist": ["mypackage"]}}}
        assert mock_write_toml.called

    @patch("twyn.config.config_handler.ConfigHandler._write_toml")
    @patch("twyn.config.config_handler.ConfigHandler._read_toml")
    def test_allowlist_add_duplicate_error(self, mock_toml: Mock, mock_write_toml: Mock) -> None:
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage"]}}}))

        config = ConfigHandler(FileHandler("some-file"))
        with pytest.raises(
            AllowlistPackageAlreadyExistsError,
            match="Package 'mypackage' is already present in the allowlist. Skipping.",
        ):
            config.add_package_to_allowlist("mypackage")

        assert not mock_write_toml.called

    @patch("twyn.config.config_handler.ConfigHandler._write_toml")
    @patch("twyn.config.config_handler.ConfigHandler._read_toml")
    def test_allowlist_remove_completely(self, mock_toml: Mock, mock_write_toml: Mock) -> None:
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage"]}}}))

        config = ConfigHandler(FileHandler("some-file"))

        config.remove_package_from_allowlist("mypackage")
        assert config._read_toml() == {"tool": {"twyn": {}}}

    @patch("twyn.config.config_handler.ConfigHandler._write_toml")
    @patch("twyn.config.config_handler.ConfigHandler._read_toml")
    def test_allowlist_remove(self, mock_toml: Mock, mock_write_toml: Mock) -> None:
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage", "another-package"]}}}))

        config = ConfigHandler(FileHandler("some-file"))

        config.remove_package_from_allowlist("mypackage")
        assert config._read_toml() == {"tool": {"twyn": {"allowlist": ["another-package"]}}}

    @patch("twyn.config.config_handler.ConfigHandler._write_toml")
    @patch("twyn.config.config_handler.ConfigHandler._read_toml")
    def test_allowlist_remove_non_existent_package_error(self, mock_toml: Mock, mock_write_toml: Mock) -> None:
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage"]}}}))

        config = ConfigHandler(FileHandler("some-file"))
        with pytest.raises(
            AllowlistPackageDoesNotExistError,
            match="Package 'mypackage2' is not present in the allowlist. Skipping.",
        ):
            config.remove_package_from_allowlist("mypackage2")

        assert not mock_write_toml.called

    @pytest.mark.parametrize("valid_selector", ["first-letter", "nearby-letter", "all"])
    def test_valid_selector_methods_accepted(self, valid_selector: str, tmp_path: Path) -> None:
        """Test that all valid selector methods are accepted."""
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text("")
        config = ConfigHandler(FileHandler(str(pyproject_toml)), enforce_file=False)

        # Should not raise any exception
        resolved_config = config.resolve_config(selector_method=valid_selector)
        assert resolved_config.selector_method == valid_selector

    def test_invalid_selector_method_rejected(self, tmp_path: Path) -> None:
        """Test that invalid selector methods are rejected with appropriate error."""
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text("")
        config = ConfigHandler(FileHandler(str(pyproject_toml)), enforce_file=False)

        with pytest.raises(InvalidSelectorMethodError) as exc_info:
            config.resolve_config(selector_method="random-selector")

        error_message = str(exc_info.value)
        assert "Invalid selector_method 'random-selector'" in error_message
        assert "Must be one of: all, first-letter, nearby-letter" in error_message

    def test_invalid_selector_method_from_config_file(self, tmp_path: Path) -> None:
        """Test that invalid selector method from config file is rejected."""
        # Create a config file with invalid selector method
        pyproject_toml = tmp_path / "pyproject.toml"
        data = """
        [tool.twyn]
        selector_method="invalid-selector"
        """
        pyproject_toml.write_text(data)

        config = ConfigHandler(FileHandler(str(pyproject_toml)))

        with pytest.raises(InvalidSelectorMethodError) as exc_info:
            config.resolve_config()

        error_message = str(exc_info.value)
        assert "Invalid selector_method 'invalid-selector'" in error_message
        assert "Must be one of: all, first-letter, nearby-letter" in error_message
