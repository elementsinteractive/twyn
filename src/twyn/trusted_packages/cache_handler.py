import json
import logging
import os
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator

from twyn.base.exceptions import PackageNormalizingError
from twyn.base.utils import normalize_packages
from twyn.file_handler.exceptions import PathIsNotFileError, PathNotFoundError
from twyn.file_handler.file_handler import FileHandler
from twyn.trusted_packages.constants import CACHE_DIR, TRUSTED_PACKAGES_MAX_RETENTION_DAYS

logger = logging.getLogger("twyn")


class CacheEntry(BaseModel):
    saved_date: str
    packages: set[str]

    @field_validator("saved_date")
    @classmethod
    def validate_saved_date(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid saved_date format: {e}") from e
        else:
            return v

    @field_validator("packages")
    @classmethod
    def validate_packages(cls, v: set[str]) -> set[str]:
        try:
            return normalize_packages(v)
        except PackageNormalizingError as e:
            raise ValueError(f"Failed to normalize packages: {e}") from e


class CacheHandler:
    """Cache class that provides basic read/write/delete operation for individual source cache files."""

    def __init__(self, cache_dir: str = CACHE_DIR) -> None:
        self.cache_dir = cache_dir

    def write_entry(self, source: str, data: CacheEntry) -> None:
        """Save cache entry to source-specific cache file."""
        file_handler = self._get_file_handler(source)
        # Ensure parent directory exists
        file_handler.file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler.write(data.model_dump_json())
        logger.debug("Successfully wrote cache data to %s", file_handler.file_path)

    def get_cache_entry(self, source: str) -> Optional[CacheEntry]:
        """Retrieve cache entry from source-specific cache file."""
        file_handler = self._get_file_handler(source)
        try:
            content = file_handler.read()
        except (PathNotFoundError, PathIsNotFileError):
            logger.debug("Cache file not found: %s", file_handler.file_path)
            return None

        try:
            json_content = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Failed to decode JSON from cache file %s: %s", file_handler.file_path, e)
            return None

        if not json_content:
            return None

        try:
            entry = CacheEntry(**json_content)
            if not self.is_entry_outdated(entry):
                return entry
        except ValidationError:
            logger.warning("Could not read cache for source %s. Cache is corrupt.", source)
            self._clear_entry(source)

        return None

    def is_entry_outdated(self, entry: CacheEntry) -> bool:
        """Check if a cache entry is outdated based on retention days."""
        try:
            saved_date = datetime.fromisoformat(entry.saved_date).date()
            days_diff = (datetime.today().date() - saved_date).days
        except (ValueError, AttributeError):
            logger.warning("Invalid date format in cache entry")
            return True
        else:
            return days_diff > TRUSTED_PACKAGES_MAX_RETENTION_DAYS

    def clear_all(self) -> None:
        """Delete all cache files in the cache directory."""
        for root, _dirs, files in os.walk(self.cache_dir):
            for file in files:
                if file.endswith(".json"):
                    FileHandler(os.path.join(root, file)).delete()

        # Remove parent directory if it exists and is empty
        cache_path = Path(self.cache_dir)
        if cache_path.exists() and cache_path.is_dir():
            try:
                cache_path.rmdir()
            except OSError:
                logger.exception("Could not delete cache directory.")

    def get_cache_file_path(self, source: str) -> str:
        """Generate cache file path for a specific source."""
        safe_filename = md5(source.encode()).hexdigest()
        return str(Path(self.cache_dir) / f"{safe_filename}.json")

    def _get_file_handler(self, source: str) -> FileHandler:
        """Get file handler for a specific source cache file."""
        cache_file_path = self.get_cache_file_path(source)
        return FileHandler(cache_file_path)

    def _clear_entry(self, source: str) -> None:
        """Delete cache file for a specific source."""
        file_handler = self._get_file_handler(source)
        file_handler.delete(delete_parent_dir=False)
