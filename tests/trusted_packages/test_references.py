import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from freezegun import freeze_time
from twyn.base.constants import DEFAULT_TOP_PYPI_PACKAGES
from twyn.trusted_packages import TopPyPiReference
from twyn.trusted_packages.cache_handler import CacheEntry, CacheHandler
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
    InvalidPyPiFormatError,
)
from twyn.trusted_packages.references import AbstractPackageReference

from tests.conftest import patch_pypi_packages_download


class TestAbstractPackageReference:
    class DummyPackageReference(AbstractPackageReference):
        """Returns always the same packages, used for testing the interface."""

        def get_packages(self) -> set[str]:
            return {"foo", "bar"}

    def test_get_packages(self) -> None:
        assert self.DummyPackageReference(source="foo", cache_handler=CacheHandler()).get_packages() == {
            "foo",
            "bar",
        }


class TestTopPyPiReference:
    @freeze_time("2025-8-21", tz_offset=0)
    def test_cache_is_saved_when_not_existing(self, tmp_path: Path) -> None:
        """Test that cache starts empty and gets filled after downloading packages."""
        cached_packages = {"numpy", "requests", "django"}
        cache_handler = CacheHandler(str(tmp_path / "cache"))
        with patch_pypi_packages_download(cached_packages) as m_pypi:
            pypi_ref = TopPyPiReference(source="pypi", cache_handler=cache_handler)

            retrieved_packages = pypi_ref.get_packages(use_cache=True)

        # The packages were downloaded and match the expected result
        assert m_pypi.call_count == 1
        assert retrieved_packages == cached_packages

        # The packages were saved to the cache file, with its associated metadata
        cache_content = cache_handler.get_cache_entry("pypi")

        assert set(cache_content.packages) == cached_packages
        assert cache_content.saved_date == "2025-08-21"

    def test_get_trusted_packages(self, tmp_path: Path) -> None:
        test_packages = ["foo", "bar", "django", "requests", "sqlalchemy"]

        with patch_pypi_packages_download(test_packages) as m_pypi:
            ref = TopPyPiReference(
                source=DEFAULT_TOP_PYPI_PACKAGES, cache_handler=CacheHandler(str(tmp_path / "cache"))
            )
            packages = ref.get_packages()

        assert packages == {"foo", "bar", "django", "requests", "sqlalchemy"}
        assert m_pypi.call_count == 1

    def test__parse_no_rows(self) -> None:
        data = {"bananas": 5}
        top_pypi = TopPyPiReference(source="foo", cache_handler=CacheHandler())

        with pytest.raises(InvalidPyPiFormatError, match="Invalid JSON format."):
            top_pypi._parse(data)

    def test_empty_packages_list_exception(self) -> None:
        with pytest.raises(
            EmptyPackagesListError,
            match="Downloaded packages list is empty",
        ):
            TopPyPiReference._parse({"rows": []})

    def test__parse_retrieves_package_names(self) -> None:
        data = {"rows": [{"project": "boto3"}, {"project": "requests"}]}
        top_pypi = TopPyPiReference(source="foo", cache_handler=CacheHandler())

        assert top_pypi._parse(data) == {"boto3", "requests"}

    @patch("requests.get")
    def test__download_json_exception(self, mock_get: Mock) -> None:
        mock_get.return_value.json.side_effect = requests.exceptions.JSONDecodeError(
            "This exception will be mapped and never shown", "", 1
        )
        top_pypi = TopPyPiReference(source="foo", cache_handler=CacheHandler())

        with pytest.raises(
            InvalidJSONError,
            match="Could not json decode the downloaded packages list",
        ):
            top_pypi._download()

    @freeze_time("2025-8-19")
    def test_get_trusted_packages_uses_valid_cache(self, tmp_path: Path) -> None:
        """Test that valid cached data is loaded and used without fetching from PyPI."""
        packages = {"requests", "flask", "django", "fastapi"}

        cache_handler = CacheHandler(str(tmp_path / "cache"))
        cache_entry = CacheEntry(saved_date="2025-08-18", packages=packages)
        cache_handler.write_entry(source="pypi", data=cache_entry)

        # Verify the cache entry was saved and can be retrieved
        retrieved_cache_entry = cache_handler.get_cache_entry("pypi")
        assert retrieved_cache_entry is not None
        assert retrieved_cache_entry.saved_date == "2025-08-18"
        assert retrieved_cache_entry.packages == packages

        with patch_pypi_packages_download(packages) as m_pypi:
            result = TopPyPiReference("pypi", cache_handler=cache_handler).get_packages(use_cache=True)

        assert m_pypi.call_count == 0
        assert result == {"flask", "fastapi", "requests", "django"}

    def test_get_packages_no_cache(self, tmp_path: Path) -> None:
        """Test that when use_cache is False, cache is not read or written, and packages are retrieved."""
        test_packages = ["numpy", "requests", "django"]
        source_url = "https://test.pypi.org/simple"

        with (
            patch.object(TopPyPiReference, "_get_packages_from_cache") as mock_get_cache,
            patch.object(TopPyPiReference, "_save_trusted_packages_to_cache") as mock_save_cache,
            patch_pypi_packages_download(test_packages) as mock_pypi,
        ):
            ref = TopPyPiReference(source=source_url, cache_handler=CacheHandler(str(tmp_path / "cache")))
            result = ref.get_packages(use_cache=False)

        assert mock_get_cache.call_count == 0
        assert mock_save_cache.call_count == 0
        assert mock_pypi.call_count == 1
        assert set(result) == set(test_packages)

    def test_cache_valid_for_fractional_days(self, tmp_path: Path) -> None:
        """Test that cache is still loaded when age is 29.7 days (not outdated) and no download occurs."""
        packages = ["numpy", "requests"]
        now = datetime.now().astimezone()
        saved_date = (now - timedelta(days=29, hours=16, minutes=48)).isoformat()  # 29.7 days ago

        cache_handler = CacheHandler(str(tmp_path / "cache"))
        cache_handler.write_entry(source="pypi", data=CacheEntry(saved_date=saved_date, packages=packages))

        with freeze_time(now), patch_pypi_packages_download(["should_not_be_used"]) as mock_download:
            ref = TopPyPiReference(source="pypi", cache_handler=cache_handler)
            loaded = ref.get_packages(use_cache=True)
        assert set(loaded) == set(packages)
        assert mock_download.call_count == 0

    def test_get_packages_downloads_when_cache_has_invalid_package_names(self, tmp_path: Path) -> None:
        """Test that packages are downloaded from source when cache contains invalid package names."""
        cache_handler = CacheHandler(str(tmp_path / "cache"))

        # Create a cache entry with invalid package names that would fail validation
        # We'll create the cache file manually with invalid data to test corruption handling
        os.makedirs(cache_handler.cache_dir, exist_ok=True)
        cache_file_path = cache_handler.get_cache_file_path("pypi")
        with open(cache_file_path, "w") as f:
            f.write('{"saved_date": "2025-01-01", "packages": ["/invalid"]}')

        # Valid packages that should be downloaded
        valid_packages = ["valid-package", "another-valid", "third-valid"]

        with patch_pypi_packages_download(valid_packages) as mock_pypi:
            ref = TopPyPiReference(source="pypi", cache_handler=cache_handler)
            result = ref.get_packages(use_cache=True)

        # Should download from source due to invalid package names in cache
        assert mock_pypi.call_count == 1
        assert result == {"valid-package", "another-valid", "third-valid"}
