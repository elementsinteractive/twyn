import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import Mock, call, patch

import httpx
import pytest
from click.testing import CliRunner
from freezegun import freeze_time
from scripts.download_packages import (  # noqa: E402
    DEPENDENCIES_DIR,
    ECOSYSTEMS,
    RETRY_ATTEMPTS,
    Ecosystem,
    InvalidJSONError,
    ServerError,
    _run,
    download,
    npm_ecosystem,
    parse_npm,
    parse_pypi,
)


@contextmanager
def patch_client(json_data: Any) -> Iterator[Mock]:
    """Context manager that patches httpx.Client.get to return mock data with specified JSON response."""
    with patch("httpx.Client.get") as mock_client:
        mock_data = Mock()
        mock_data.json.return_value = json_data
        mock_client.return_value = mock_data
        yield mock_client


@contextmanager
def patch_client_error(error: Exception) -> Iterator[Mock]:
    """Context manager that patches httpx.Client.get to raise specified error on status check."""
    with patch("httpx.Client.get") as mock_client:
        mock_data = Mock()
        mock_data.raise_for_status.side_effect = error
        mock_client.return_value = mock_data
        yield mock_client


@contextmanager
def patch_save_to_file() -> Iterator[Mock]:
    """Context manager that patches json.dump to capture file saving operations."""
    with patch("json.dump") as m_json:
        yield m_json


@contextmanager
def patch_open_file() -> Iterator[Mock]:
    """Context manager that patches builtins.open to capture file opening operations."""
    with patch("builtins.open") as mock_open:
        yield mock_open


@contextmanager
def patch_npm_ecosystem(data: dict[str, Any]) -> Iterator[None]:
    """Context manager that temporarily modifies the npm ecosystem configuration for testing."""
    with (
        patch.dict(
            ECOSYSTEMS,
            {"npm": Ecosystem(**npm_ecosystem.__dict__ | data)},
        ),
    ):
        yield


@freeze_time("2025-01-01")
class TestDownload:
    def test_pypi_download(self) -> None:
        """Test downloading PyPI packages and verifying the correct API call and data saving."""
        data = {
            "rows": [
                {"project": "requests", "download_count": 12345},
                {"project": "setuptools", "download_count": 8765},
            ]
        }
        with patch_client(data) as m_client, patch_save_to_file() as m_save, patch_open_file() as m_open:
            _run("pypi")

        # Check the HTTP request with its parameters
        assert m_client.call_count == 1
        assert m_client.call_args == call(
            "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json", params={}
        )

        # Check the file path
        assert m_open.call_args_list[0] == call(str(Path(DEPENDENCIES_DIR) / "pypi.json"), "w")

        # Check the content of the file
        assert m_save.call_count == 1
        assert m_save.call_args[0][0]["date"] == "2025-01-01T00:00:00+00:00"
        assert set(m_save.call_args[0][0]["packages"]) == {"setuptools", "requests"}
        assert m_save.call_args[0][1] == m_open().__enter__()

    def test_npm_download(self) -> None:
        """Test downloading npm packages with pagination and verifying the correct API call and data saving."""
        data = [
            {"name": "lodash", "downloads": 12345},
            {"name": "@aws/sdk", "downloads": 98765},
        ]
        with (
            patch_client(data) as m_client,
            patch_save_to_file() as m_save,
            patch_open_file() as m_open,
            patch_npm_ecosystem({"pages": 1}),
        ):
            _run("npm")

        # Check the HTTP request with its parameters
        assert m_client.call_count == 1
        assert m_client.call_args == call(
            "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages",
            params={"per_page": 100, "sort": "downloads", "page": 1},
        )

        # Check the file path
        assert m_open.call_args_list[0] == call(str(Path(DEPENDENCIES_DIR) / "npm.json"), "w")

        # Check the content of the file
        assert m_save.call_count == 1
        assert m_save.call_args[0][0]["date"] == "2025-01-01T00:00:00+00:00"
        assert set(m_save.call_args[0][0]["packages"]) == {"@aws/sdk", "lodash"}
        assert m_save.call_args[0][1] == m_open().__enter__()

    def test_invalid_ecosystem(self) -> None:
        """Test that a KeyError is raised when trying to run with an invalid ecosystem."""
        with pytest.raises(KeyError):
            _run("asdf")

    def test_invalid_pypi_json_format(self) -> None:
        """Test that InvalidJSONError is raised when PyPI JSON data has invalid format."""
        with pytest.raises(InvalidJSONError):
            parse_pypi({})

    def test_invalid_npm_json_format(self) -> None:
        """Test that InvalidJSONError is raised when npm JSON data has invalid format."""
        with pytest.raises(InvalidJSONError):
            parse_npm([{"key": "val"}])

    def test_invalid_downloaded_json(self) -> None:
        """Test that InvalidJSONError is raised when downloaded JSON cannot be parsed."""
        with patch("httpx.Client.get") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_client.return_value = mock_response
            with pytest.raises(InvalidJSONError):
                _run("pypi")

    def test_retry_mechanism_with_server_errors(self) -> None:
        """Test that it will retry as many times as attempts defined and raise an exception afterwards."""
        mock_response = Mock()
        mock_response.is_server_error = True
        mock_response.status_code = 500

        server_error = httpx.HTTPStatusError("Server Error", request=Mock(), response=mock_response)

        with (
            patch_client_error(server_error) as mock_client,
            patch("scripts.download_packages.RETRY_WAIT_JITTER", 0),
            patch("scripts.download_packages.RETRY_WAIT_EXP_BASE", 1),
            patch("scripts.download_packages.RETRY_WAIT_MAX", 0),
        ):
            with pytest.raises(ServerError):
                _run("pypi")

            assert mock_client.call_count == RETRY_ATTEMPTS

    def test_npm_download_with_multiple_pages(self) -> None:
        """Test that the script will iterate through pages if provided."""
        page1_data = [
            {"name": "lodash", "downloads": 12345},
            {"name": "@aws/sdk", "downloads": 98765},
        ]
        page2_data = [
            {"name": "react", "downloads": 54321},
            {"name": "express", "downloads": 87654},
        ]

        with (
            patch_client(None) as m_client,  # We'll configure the side_effect below
            patch_save_to_file() as m_save,
            patch_open_file() as m_open,
            patch_npm_ecosystem({"pages": 2}),
        ):
            # Configure the mock to return different data for each call
            mock_responses = []
            for data in [page1_data, page2_data]:
                mock_response = Mock()
                mock_response.json.return_value = data
                mock_responses.append(mock_response)

            m_client.side_effect = mock_responses

            _run("npm")

        assert m_client.call_count == 2

        assert m_client.call_args_list == [
            call(
                "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages",
                params={"per_page": 100, "sort": "downloads", "page": 1},
            ),
            call(
                "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages",
                params={"per_page": 100, "sort": "downloads", "page": 2},
            ),
        ]

        # Verify that all packages from all pages were collected
        assert m_save.call_count == 1
        assert m_save.call_args[0][0]["date"] == "2025-01-01T00:00:00+00:00"
        assert set(m_save.call_args[0][0]["packages"]) == {"lodash", "@aws/sdk", "react", "express"}
        assert m_save.call_args[0][1] == m_open().__enter__()


class TestCli:
    def test_non_existing_ecosystem_error(self) -> None:
        """Test that an error is raised when a non-existing ecosystem is introduced."""
        runner = CliRunner()
        result = runner.invoke(download, ["invalid_ecosystem"])

        assert result.exit_code != 0
        assert "Not a valid ecosystem" in result.output

    @freeze_time("2025-01-01")
    def test_cli(self) -> None:
        """Test the script can be run through the cli and contents are saved to file."""
        runner = CliRunner()

        data = {
            "rows": [
                {"project": "requests", "download_count": 12345},
                {"project": "setuptools", "download_count": 8765},
            ]
        }
        with patch_client(data), patch_save_to_file() as m_save, patch_open_file() as m_open:
            result = runner.invoke(download, ["pypi"])

        assert result.exit_code == 0

        assert m_save.call_count == 1
        assert m_save.call_args[0][0]["date"] == "2025-01-01T00:00:00+00:00"
        assert set(m_save.call_args[0][0]["packages"]) == {"setuptools", "requests"}
        assert m_save.call_args[0][1] == m_open().__enter__()
