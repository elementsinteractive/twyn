import dataclasses
from copy import deepcopy
from unittest.mock import patch

import pytest
from tomlkit import TOMLDocument, dumps, parse
from twyn.base.constants import DEFAULT_TOP_PYPI_PACKAGES, AvailableLoggingLevels
from twyn.core.config_handler import ConfigHandler, ReadTwynConfiguration, TwynConfiguration
from twyn.core.exceptions import (
    AllowlistPackageAlreadyExistsError,
    AllowlistPackageDoesNotExistError,
    TOMLError,
)


class TestConfig:
    def throw_exception(self):
        raise FileNotFoundError

    @patch("twyn.core.config_handler.ConfigHandler._get_toml_file_pointer")
    def test_enforce_file_error(self, mock_is_file):
        mock_is_file.side_effect = self.throw_exception
        with pytest.raises(TOMLError):
            ConfigHandler(enforce_file=True).resolve_config()

    @patch("twyn.core.config_handler.ConfigHandler._get_toml_file_pointer")
    def test_no_enforce_file_on_non_existent_file(self, mock_is_file):
        """Resolving the config without enforcing the file to be present gives you defaults."""
        mock_is_file.side_effect = self.throw_exception
        config = ConfigHandler(enforce_file=False).resolve_config()

        assert config == TwynConfiguration(
            dependency_file=None,
            selector_method="all",
            logging_level=AvailableLoggingLevels.warning,
            allowlist=set(),
            pypi_reference=DEFAULT_TOP_PYPI_PACKAGES,
        )

    def test_config_raises_for_unknown_file(self):
        with pytest.raises(TOMLError):
            ConfigHandler(file_path="non-existent-file.toml").resolve_config()

    def test_read_config_values(self, pyproject_toml_file):
        config = ConfigHandler(file_path=pyproject_toml_file).resolve_config()
        assert config.dependency_file == "my_file.txt"
        assert config.selector_method == "my_selector"
        assert config.logging_level == AvailableLoggingLevels.debug
        assert config.allowlist == {"boto4", "boto2"}

    def test_get_twyn_data_from_file(self, pyproject_toml_file):
        handler = ConfigHandler(file_path=pyproject_toml_file)

        toml = handler._read_toml()
        twyn_data = ConfigHandler(file_path=pyproject_toml_file)._get_read_config(toml)
        assert twyn_data == ReadTwynConfiguration(
            dependency_file="my_file.txt",
            selector_method="my_selector",
            logging_level="debug",
            allowlist={"boto4", "boto2"},
            pypi_reference=None,
        )

    def test_write_toml(self, pyproject_toml_file):
        handler = ConfigHandler(file_path=pyproject_toml_file)
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
                    "selector_method": "my_selector",
                    "logging_level": "debug",
                    "allowlist": {},
                    "pypi_reference": DEFAULT_TOP_PYPI_PACKAGES,
                },
            }
        }


class TestAllowlistConfigHandler:
    @patch("twyn.core.config_handler.ConfigHandler._write_toml")
    @patch("twyn.core.config_handler.ConfigHandler._read_toml")
    def test_allowlist_add(self, mock_toml, mock_write_toml):
        mock_toml.return_value = TOMLDocument()

        config = ConfigHandler()

        config.add_package_to_allowlist("mypackage")

        final_toml = config._read_toml()

        assert final_toml == {"tool": {"twyn": {"allowlist": ["mypackage"]}}}
        assert mock_write_toml.called

    @patch("twyn.core.config_handler.ConfigHandler._write_toml")
    @patch("twyn.core.config_handler.ConfigHandler._read_toml")
    def test_allowlist_add_duplicate_error(self, mock_toml, mock_write_toml):
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage"]}}}))

        config = ConfigHandler()
        with pytest.raises(
            AllowlistPackageAlreadyExistsError,
            match="Package 'mypackage' is already present in the allowlist. Skipping.",
        ):
            config.add_package_to_allowlist("mypackage")

        assert not mock_write_toml.called

    @patch("twyn.core.config_handler.ConfigHandler._write_toml")
    @patch("twyn.core.config_handler.ConfigHandler._read_toml")
    def test_allowlist_remove_completely(self, mock_toml, mock_write_toml):
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage"]}}}))

        config = ConfigHandler()

        config.remove_package_from_allowlist("mypackage")
        assert config._read_toml() == {"tool": {"twyn": {}}}

    @patch("twyn.core.config_handler.ConfigHandler._write_toml")
    @patch("twyn.core.config_handler.ConfigHandler._read_toml")
    def test_allowlist_remove(self, mock_toml, mock_write_toml):
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage", "another-package"]}}}))

        config = ConfigHandler()

        config.remove_package_from_allowlist("mypackage")
        assert config._read_toml() == {"tool": {"twyn": {"allowlist": ["another-package"]}}}

    @patch("twyn.core.config_handler.ConfigHandler._write_toml")
    @patch("twyn.core.config_handler.ConfigHandler._read_toml")
    def test_allowlist_remove_non_existent_package_error(self, mock_toml, mock_write_toml):
        mock_toml.return_value = parse(dumps({"tool": {"twyn": {"allowlist": ["mypackage"]}}}))

        config = ConfigHandler()
        with pytest.raises(
            AllowlistPackageDoesNotExistError,
            match="Package 'mypackage2' is not present in the allowlist. Skipping.",
        ):
            config.remove_package_from_allowlist("mypackage2")

        assert not mock_write_toml.called
