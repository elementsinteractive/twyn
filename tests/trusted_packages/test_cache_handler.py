from datetime import datetime, timedelta
from pathlib import Path

import pytest
from freezegun import freeze_time
from pydantic import ValidationError
from twyn.trusted_packages.cache_handler import CacheEntry, CacheHandler


@freeze_time("2025-01-01")
class TestCacheHandler:
    def test_create_valid_cache_entry(self, tmp_path: Path) -> None:
        """Test reading valid JSON from cache file."""
        source = "https://source.com"

        cache_handler = CacheHandler(str(tmp_path))
        entry = CacheEntry(saved_date="2025-01-01", packages={"requests"})

        cache_handler.write_entry(source, entry)
        result = cache_handler.get_cache_entry(source)

        assert result.packages == entry.packages
        assert result.saved_date == entry.saved_date
        fpath = tmp_path / f"{cache_handler.get_cache_file_path(source)}"
        assert fpath.exists()

    def test_create_directory(self, tmp_path: Path) -> None:
        """Test reading valid JSON from cache file."""
        source = "https://source.com"

        cache_handler = CacheHandler(str(tmp_path / "my-path"))
        entry = CacheEntry(saved_date="2025-01-01", packages={"requests"})

        cache_handler.write_entry(source, entry)

        fpath = tmp_path / f"{cache_handler.get_cache_file_path(source)}"
        assert fpath.exists()

    def test_read_nonexistent_file(self) -> None:
        """Test reading non-existent file raises FileNotFoundError."""
        cache_handler = CacheHandler("fakedir")

        content = cache_handler.get_cache_entry("https://source.com")
        assert content is None

    def test_get_non_existent_entry_in_correct_source(self, tmp_path: Path) -> None:
        cache_handler = CacheHandler(str(tmp_path))

        content = cache_handler.get_cache_entry("https://source.com")
        assert content is None

    def test_multiple_sources_support(self, tmp_path: Path) -> None:
        """Test that cache handler supports multiple sources simultaneously."""
        cache_handler = CacheHandler(tmp_path)

        # Create entries for different sources
        source1 = "pypi"
        packages1 = {"numpy", "pandas", "requests"}
        date1 = datetime.now().date().isoformat()
        entry1 = CacheEntry(saved_date=date1, packages=packages1)

        source2 = "pypi2"
        packages2 = {"test-package", "dev-tools", "beta-lib"}
        entry2 = CacheEntry(saved_date=datetime.now().date().isoformat(), packages=packages2)

        # Write entries to cache
        cache_handler.write_entry(source1, entry1)
        cache_handler.write_entry(source2, entry2)

        # Verify each source can be retrieved independently and each one was written to its file
        retrieved_entry1 = cache_handler.get_cache_entry(source1)
        assert retrieved_entry1 is not None
        assert retrieved_entry1.packages == packages1
        assert retrieved_entry1.saved_date == date1

        retrieved_entry2 = cache_handler.get_cache_entry(source2)
        assert retrieved_entry2 is not None
        assert retrieved_entry2.packages == packages2

        # Update an entry
        packages1_new = {"new-package"}
        date1_new = datetime(2025, 1, 2).date().isoformat()

        assert date1 != date1_new
        entry1_new = CacheEntry(saved_date=date1_new, packages=packages1_new)
        cache_handler.write_entry(source1, entry1_new)

        new_cache_content = cache_handler.get_cache_entry(source1)

        # Check old entry is updated with new content
        assert new_cache_content.packages == entry1_new.packages
        assert new_cache_content.saved_date == entry1_new.saved_date

        # Check that the other entry has not been modified
        retrieved_entry2 = cache_handler.get_cache_entry(source2)
        assert retrieved_entry2 is not None
        assert retrieved_entry2.packages == packages2

    def test_is_entry_outdated_with_fresh_entry(self, tmp_path: Path) -> None:
        """Test is_entry_outdated returns False for fresh cache entry."""
        # Create a fresh entry (today's date)
        fresh_date = datetime.today().date().isoformat()
        entry = CacheEntry(saved_date=fresh_date, packages={"package1", "package2"})

        cache_handler = CacheHandler(str(tmp_path))

        assert cache_handler.is_entry_outdated(entry) is False

    def test_is_entry_outdated_with_old_entry(self, tmp_path: Path) -> None:
        """Test is_entry_outdated returns True for old cache entry."""
        # Create an old entry (40 days ago, assuming default retention is 30 days)
        old_date = (datetime.today().date() - timedelta(days=40)).isoformat()
        entry = CacheEntry(saved_date=old_date, packages={"package1", "package2"})

        cache_handler = CacheHandler(str(tmp_path))

        assert cache_handler.is_entry_outdated(entry) is True

    def test_is_entry_outdated_with_invalid_date_format(self) -> None:
        # Create an entry with invalid date format
        with pytest.raises(ValidationError):
            CacheEntry(saved_date="invalid-date-format", packages={"package1"})

    def test_clear_all_removes_all_cache_files(self, tmp_path: Path) -> None:
        """Test clear_all removes all cache files and directory."""
        cache_handler = CacheHandler(str(tmp_path))

        # Create multiple cache entries
        sources = ["source1", "source2", "source3"]
        for source in sources:
            entry = CacheEntry(saved_date="2025-01-01", packages={"package"})
            cache_handler.write_entry(source, entry)

        # Verify files exist
        for source in sources:
            assert cache_handler.get_cache_entry(source) is not None

        # Clear all cache
        cache_handler.clear_all()

        # Verify all entries are gone
        for source in sources:
            assert cache_handler.get_cache_entry(source) is None

        # Verify cache directory is removed
        assert not tmp_path.exists() or not any(tmp_path.iterdir())

    def test_clear_all_with_empty_cache_directory(self, tmp_path: Path) -> None:
        """Test clear_all handles empty cache directory gracefully."""
        cache_handler = CacheHandler(str(tmp_path))

        # Call clear_all on empty directory
        cache_handler.clear_all()

        # Should not raise any errors
        assert True
