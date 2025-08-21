import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
import requests
from freezegun import freeze_time
from twyn.base.constants import DEFAULT_TOP_PYPI_PACKAGES
from twyn.trusted_packages import TopPyPiReference
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
    InvalidPyPiFormatError,
)
from twyn.trusted_packages.references import AbstractPackageReference

from tests.conftest import patch_pypi_packages_download


class DummyFileHandler:
    def __init__(self, content: Any) -> None:
        self._content = content

    def read(self):
        return self._content


class TestAbstractPackageReference:
    class DummyPackageReference(AbstractPackageReference):
        """Returns always the same packages, used for testing the interface."""

        def get_packages(self) -> set[str]:
            return {"foo", "bar"}

    def test_get_packages(self) -> None:
        assert self.DummyPackageReference(source="foo").get_packages() == {"foo", "bar"}


class TestTopPyPiReference:
    @freeze_time("2025-8-21", tz_offset=0)
    def test_cache_is_saved_when_not_existing(self, tmp_cache_file: Path) -> None:
        """Test that cache starts empty and gets filled after downloading packages."""
        # Verify cache file is initially empty
        assert tmp_cache_file.exists() is False

        cached_packages = {"numpy", "requests", "django"}

        with patch_pypi_packages_download(cached_packages) as m_pypi:
            pypi_ref = TopPyPiReference(source="https://test.pypi.org/simple")

            retrieved_packages = pypi_ref.get_packages(use_cache=True)

        # The packages were downloaded and match the expected result
        assert m_pypi.call_count == 1
        assert retrieved_packages == cached_packages

        # The packages were saved to the cache file, with its associated metadata
        cache_content = json.loads(tmp_cache_file.read_text())

        assert cache_content["source"] == "https://test.pypi.org/simple"
        assert set(cache_content["data"]["packages"]) == cached_packages
        assert cache_content["data"]["count"] == len(cached_packages)
        assert cache_content["data"]["saved_date"] == "2025-08-21"

    def test_get_trusted_packages(self) -> None:
        test_packages = ["foo", "bar", "django", "requests", "sqlalchemy"]

        with patch_pypi_packages_download(test_packages) as m_pypi:
            ref = TopPyPiReference(source=DEFAULT_TOP_PYPI_PACKAGES)
            packages = ref.get_packages()

        assert packages == {"foo", "bar", "django", "requests", "sqlalchemy"}
        assert m_pypi.call_count == 1

    def test__parse_no_rows(self):
        data = {"bananas": 5}
        top_pypi = TopPyPiReference(source="foo")

        with pytest.raises(InvalidPyPiFormatError, match="Invalid JSON format."):
            top_pypi._parse(data)

    def test_empty_packages_list_exception(self) -> None:
        with pytest.raises(
            EmptyPackagesListError,
            match="Downloaded packages list is empty",
        ):
            TopPyPiReference._parse({"rows": []})

    def test__parse_retrieves_package_names(self):
        data = {"rows": [{"project": "boto3"}, {"project": "requests"}]}
        top_pypi = TopPyPiReference(source="foo")

        assert top_pypi._parse(data) == {"boto3", "requests"}

    @patch("requests.get")
    def test__download_json_exception(self, mock_get: Mock) -> None:
        mock_get.return_value.json.side_effect = requests.exceptions.JSONDecodeError(
            "This exception will be mapped and never shown", "", 1
        )
        top_pypi = TopPyPiReference(source="foo")

        with pytest.raises(
            InvalidJSONError,
            match="Could not json decode the downloaded packages list",
        ):
            top_pypi._download()

    @freeze_time("2025-8-19")
    def test_get_trusted_packages_uses_valid_cache(self, tmp_cache_file: Path) -> None:
        """Test that valid cached data is loaded and used without fetching from PyPI."""
        packages = ["requests", "flask", "django", "fastapi"]

        cached_data = {
            "source": DEFAULT_TOP_PYPI_PACKAGES,
            "data": {
                "packages": packages,
                "count": 4,
                "saved_date": "2025-08-19",  # yesterday
            },
        }

        tmp_cache_file.write_text(json.dumps(cached_data))
        with patch_pypi_packages_download(packages) as m_pypi:
            result = TopPyPiReference("").get_packages(use_cache=True)

        assert m_pypi.call_count == 0
        assert result == {"flask", "fastapi", "requests", "django"}

    def test_get_packages_no_cache(self):
        """Test that when use_cache is False, cache is not read or written, and packages are retrieved."""
        test_packages = ["numpy", "requests", "django"]
        source_url = "https://test.pypi.org/simple"

        with (
            patch.object(TopPyPiReference, "_get_packages_from_cache") as mock_get_cache,
            patch.object(TopPyPiReference, "_save_trusted_packages_to_file") as mock_save_cache,
            patch_pypi_packages_download(test_packages) as mock_pypi,
        ):
            ref = TopPyPiReference(source=source_url)
            result = ref.get_packages(use_cache=False)

        assert mock_get_cache.call_count == 0
        assert mock_save_cache.call_count == 0
        assert mock_pypi.call_count == 1
        assert set(result) == set(test_packages)

    def test_cache_valid_for_fractional_days(self, tmp_cache_file: Path) -> None:
        """Test that cache is still loaded when age is 29.7 days (not outdated) and no download occurs."""
        test_packages = ["numpy", "requests"]
        now = datetime.now().astimezone()
        saved_date = (now - timedelta(days=29, hours=16, minutes=48)).isoformat()  # 29.7 days ago

        cache_data = {
            "source": DEFAULT_TOP_PYPI_PACKAGES,
            "data": {
                "packages": test_packages,
                "count": len(test_packages),
                "saved_date": saved_date,
            },
        }
        tmp_cache_file.write_text(json.dumps(cache_data))

        with freeze_time(now), patch_pypi_packages_download(["should_not_be_used"]) as mock_download:
            ref = TopPyPiReference(source=DEFAULT_TOP_PYPI_PACKAGES)
            loaded = ref.get_packages(use_cache=True)
        assert set(loaded) == set(test_packages)
        assert mock_download.call_count == 0

    def test_load_trusted_packages_from_file_invalid_packages_type(self) -> None:
        # data['packages'] is not iterable (e.g., None or int)
        bad_json = '{"data": {"packages": null, "count": 1, "saved_date": "2025-08-21"}}'
        handler = DummyFileHandler(bad_json)
        ref = TopPyPiReference(source="dummy")
        pkgs, outdated = ref._load_trusted_packages_from_file(handler)
        assert pkgs == set()
        assert outdated is True

    def test_load_trusted_packages_from_file_invalid_json(self) -> None:
        handler = DummyFileHandler("{invalid json")
        ref = TopPyPiReference(source="dummy")
        pkgs, outdated = ref._load_trusted_packages_from_file(handler)
        assert pkgs == set()
        assert outdated is True

    def test_load_trusted_packages_from_file_missing_data_key(self) -> None:
        bad_json = '{"not_data": {}}'
        handler = DummyFileHandler(bad_json)
        ref = TopPyPiReference(source="dummy")
        pkgs, outdated = ref._load_trusted_packages_from_file(handler)
        assert pkgs == set()
        assert outdated is True

    def test_load_trusted_packages_from_file_missing_saved_date(self) -> None:
        bad_json = '{"data": {"packages": ["foo"], "count": 1}}'
        handler = DummyFileHandler(bad_json)
        ref = TopPyPiReference(source="dummy")
        pkgs, outdated = ref._load_trusted_packages_from_file(handler)
        assert pkgs == set()
        assert outdated is True

    def test_load_trusted_packages_from_file_invalid_date_format(self) -> None:
        bad_json = '{"data": {"packages": ["foo"], "count": 1, "saved_date": "not-a-date"}}'
        handler = DummyFileHandler(bad_json)
        ref = TopPyPiReference(source="dummy")
        pkgs, outdated = ref._load_trusted_packages_from_file(handler)
        assert pkgs == set()
        assert outdated is True
