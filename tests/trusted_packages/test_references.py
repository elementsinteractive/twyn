import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from freezegun import freeze_time
from twyn.trusted_packages import TopNpmReference, TopPyPiReference
from twyn.trusted_packages.cache_handler import CacheEntry, CacheHandler
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
    PackageNormalizingError,
)
from twyn.trusted_packages.references.base import AbstractPackageReference, NormalizedPackages

from tests.conftest import patch_npm_packages_download, patch_pypi_packages_download


class TestAbstractPackageReference:
    class DummyPackageReference(AbstractPackageReference):
        """Returns always the same packages, used for testing the interface."""

        def get_packages(self) -> NormalizedPackages:
            return NormalizedPackages(packages={"foo", "bar"})

        @staticmethod
        def normalize_packages(packages: set[str]) -> NormalizedPackages:
            return NormalizedPackages(packages=packages)

    def test_get_packages(self) -> None:
        result = self.DummyPackageReference(source="foo", cache_handler=CacheHandler()).get_packages()
        assert set(result) == {"foo", "bar"}

    @freeze_time("2025-8-19")
    def test_get_trusted_packages_uses_valid_cache(self, tmp_path: Path) -> None:
        """Test that valid cached data is loaded and used without fetching from PyPI."""
        packages = ["requests", "flask", "django", "fastapi"]

        cache_handler = CacheHandler(str(tmp_path / "cache"))
        cache_entry = CacheEntry(saved_date="2025-08-18", packages=packages)
        cache_handler.write_entry(source="pypi", data=cache_entry)

        # Verify the cache entry was saved and can be retrieved
        retrieved_cache_entry = cache_handler.get_cache_entry("pypi")
        assert retrieved_cache_entry is not None
        assert retrieved_cache_entry.saved_date == "2025-08-18"
        assert retrieved_cache_entry.packages == set(packages)

        with patch_pypi_packages_download(packages) as m_pypi:
            result = TopPyPiReference("pypi", cache_handler=cache_handler).get_packages()

        assert m_pypi.call_count == 0
        assert set(result) == {"flask", "fastapi", "requests", "django"}

    def test_get_packages_no_cache(self) -> None:
        """Test that when use_cache is False, cache is not read or written, and packages are retrieved."""
        test_packages = ["numpy", "requests", "django"]
        source_url = "https://test.pypi.org/simple"

        with (
            patch("twyn.trusted_packages.cache_handler.CacheHandler.get_cache_entry") as mock_get_cache,
            patch("twyn.trusted_packages.cache_handler.CacheHandler.write_entry") as mock_save_cache,
            patch_pypi_packages_download(test_packages) as mock_pypi,
        ):
            ref = TopPyPiReference(source=source_url)
            result = ref.get_packages()

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
            loaded = ref.get_packages()
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
            result = ref.get_packages()

        # Should download from source due to invalid package names in cache
        assert mock_pypi.call_count == 1
        assert set(result) == {"valid-package", "another-valid", "third-valid"}

    @freeze_time("2025-8-21", tz_offset=0)
    def test_cache_is_saved_when_not_existing(self, tmp_path: Path) -> None:
        """Test that cache starts empty and gets filled after downloading packages."""
        cached_packages = ["numpy", "requests", "django"]
        cache_handler = CacheHandler(str(tmp_path / "cache"))
        with patch_pypi_packages_download(cached_packages) as m_pypi:
            pypi_ref = TopPyPiReference(source="pypi", cache_handler=cache_handler)

            retrieved_packages = pypi_ref.get_packages()

        # The packages were downloaded and match the expected result
        assert m_pypi.call_count == 1
        assert set(retrieved_packages) == set(cached_packages)

        # The packages were saved to the cache file, with its associated metadata
        cache_content = cache_handler.get_cache_entry("pypi")

        assert set(cache_content.packages) == set(cached_packages)
        assert cache_content.saved_date == "2025-08-21"

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

    def test_get_packages_no_packages_key(self) -> None:
        top_pypi = TopPyPiReference(source="foo", cache_handler=CacheHandler())

        with patch("twyn.trusted_packages.TopPyPiReference._download") as mock_download:
            mock_download.return_value = {}
            with pytest.raises(InvalidJSONError, match="`packages` key not in JSON."):
                top_pypi.get_packages()

    def test_empty_packages_list_exception(self) -> None:
        with (
            pytest.raises(
                EmptyPackagesListError,
                match="Downloaded packages list is empty",
            ),
            patch_pypi_packages_download([]),
        ):
            TopPyPiReference().get_packages()


class TestTopPyPiReference:
    def test_get_trusted_packages(self, tmp_path: Path) -> None:
        test_packages = ["foo", "bar", "django", "requests", "sqlalchemy"]

        with patch_pypi_packages_download(test_packages) as m_pypi:
            ref = TopPyPiReference(cache_handler=CacheHandler(str(tmp_path / "cache")))
            packages = ref.get_packages()

        assert set(packages) == {"foo", "bar", "django", "requests", "sqlalchemy"}
        assert m_pypi.call_count == 1

    @pytest.mark.parametrize(
        "package_name",
        [
            "my.package",
            "my-package",
            "my_package",
            "My.Package",
        ],
    )
    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_normalize_package_when_loaded_from_cache(
        self, mock_get_packages_from_cache: Mock, package_name: Mock, tmp_path: Path
    ) -> None:
        mock_get_packages_from_cache.return_value = {package_name}

        with patch_pypi_packages_download([]) as m_pypi:
            ref = TopPyPiReference(cache_handler=CacheHandler(str(tmp_path / "cache")))
            packages = ref.get_packages()

        assert set(packages) == {"my-package"}
        assert m_pypi.call_count == 0
        assert mock_get_packages_from_cache.call_count == 1

    @pytest.mark.parametrize(
        "package_name",
        [
            "my.package",
            "my-package",
            "my_package",
            "My.Package",
        ],
    )
    @patch("twyn.trusted_packages.TopPyPiReference._get_packages_from_cache_if_enabled")
    def test_normalize_package_when_downloaded(
        self, mock_get_packages_from_cache: Mock, package_name: Mock, tmp_path: Path
    ) -> None:
        mock_get_packages_from_cache.return_value = set()

        with patch_pypi_packages_download([package_name]) as m_pypi:
            ref = TopPyPiReference()
            packages = ref.get_packages()

        assert set(packages) == {"my-package"}
        assert m_pypi.call_count == 1
        assert mock_get_packages_from_cache.call_count == 1

    def test_normalize_package_invalid_name_raises(self) -> None:
        ref = TopPyPiReference()
        with pytest.raises(PackageNormalizingError):
            ref.normalize_packages({"INVALID PACKAGE NAME!"})


class TestTopNpmReference:
    def test_get_trusted_packages(self, tmp_path: Path) -> None:
        """Test downloading packages and verify all packages are saved to cache in their original form."""
        test_packages = ["foo", "bar", "react", "express", "lodash", "@aws/sdk"]

        cache_handler = CacheHandler(str(tmp_path / "cache"))
        with patch_npm_packages_download(test_packages) as m_npm:
            ref = TopNpmReference(cache_handler=cache_handler)
            packages = ref.get_packages()

        # Verify packages were downloaded
        assert set(packages) == {"foo", "bar", "react", "express", "lodash", "@aws/sdk"}
        assert m_npm.call_count == 1

        # Verify cache entry was created with all packages in their original form
        cache_entry = cache_handler.get_cache_entry(ref.source)
        assert cache_entry is not None
        assert cache_entry.packages == {"foo", "bar", "react", "express", "lodash", "@aws/sdk"}

    def test_normalize_package_invalid_name_raises(self) -> None:
        ref = TopNpmReference()
        with pytest.raises(PackageNormalizingError):
            ref.normalize_packages({"INVALID PACKAGE NAME!"})
