import json
import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

import requests

from twyn.base.utils import _normalize_packages
from twyn.file_handler.file_handler import FileHandler
from twyn.trusted_packages.constants import TRUSTED_PACKAGES_FILE_PATH, TRUSTED_PACKAGES_MAX_RETENTION_DAYS
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidCacheError,
    InvalidJSONError,
    InvalidPyPiFormatError,
)

logger = logging.getLogger("twyn")


class AbstractPackageReference(ABC):
    """Represents a reference to retrieve trusted packages from."""

    def __init__(self, source: str) -> None:
        self.source = source

    @abstractmethod
    def get_packages(self, use_cache: bool = True) -> set[str]:
        """Return the names of the trusted packages available in the reference."""


class TopPyPiReference(AbstractPackageReference):
    """Top PyPi packages retrieved from an online source."""

    def get_packages(self, use_cache: bool = True) -> set[str]:
        """Download and parse online source of top Python Package Index packages."""
        packages_to_use = set()
        if use_cache:
            trusted_packages_file = FileHandler(TRUSTED_PACKAGES_FILE_PATH)
            packages_to_use = self._get_packages_from_cache(trusted_packages_file)
            # we don't save the cache here, we keep it as it is so the date remains the original one.

        if not packages_to_use:
            # no cache usage, no cache hit (non-existent or outdated) or cache was empty.
            logger.info("Fetching trusted packages from PyPI reference...")
            packages_to_use = self._parse(self._download())
            if use_cache:
                self._save_trusted_packages_to_file(packages_to_use, trusted_packages_file, self.source)

        normalized_packages = _normalize_packages(packages_to_use)
        return normalized_packages

    def _is_content_outdated(self, content_date: date) -> bool:
        """Check if cached content is outdated based on retention days."""
        days_diff = (datetime.today().date() - content_date).days
        return days_diff > TRUSTED_PACKAGES_MAX_RETENTION_DAYS

    def _save_trusted_packages_to_file(self, packages: set[str], file_handler: FileHandler, source: str) -> None:
        """Save trusted packages to JSON file with timestamp."""
        trusted_data = {
            "source": source,
            "data": {
                "packages": list(packages),
                "count": len(packages),
                "saved_date": datetime.now().date().isoformat(),
            },
        }
        file_handler.file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler.write(json.dumps(trusted_data))
        logger.debug("Saved %d trusted packages to %s", len(packages), file_handler.file_path)

    def _load_trusted_packages_from_file(self, file_handler: FileHandler) -> tuple[set[str], bool]:
        """Load trusted packages from JSON file and check if it's outdated."""
        try:
            try:
                trusted_packages_raw_content = json.loads(file_handler.read())
            except json.JSONDecodeError as e:
                raise InvalidCacheError("Could not decode cache.") from e

            try:
                data = trusted_packages_raw_content["data"]
                saved_date_str = data["saved_date"]
            except KeyError as e:
                raise InvalidCacheError("Invalid cache format.") from e

            try:
                saved_date = datetime.fromisoformat(saved_date_str).date()
            except ValueError as e:
                raise InvalidCacheError("Cache saved date is invalid.") from e

            try:
                packages = set(data["packages"])
            except TypeError as e:
                raise InvalidCacheError("Invalid format in cached packages") from e

            is_outdated = self._is_content_outdated(saved_date)

        except InvalidCacheError as e:
            logger.warning("Error reading cached trusted packages: %s", e)
            return set(), True
        else:
            if is_outdated:
                logger.info("Cached trusted packages are outdated (saved: %s)", saved_date)
            else:
                logger.debug("Using cached trusted packages from %s", saved_date)

            return packages, is_outdated

    def _get_packages_from_cache(self, trusted_packages_file: FileHandler) -> set[str]:
        """Get packages from cache file if it's present and up to date."""
        if trusted_packages_file.exists():
            packages_from_cache, is_outdated = self._load_trusted_packages_from_file(trusted_packages_file)
            if not is_outdated:
                return packages_from_cache

        return set()

    def _download(self) -> dict[str, Any]:
        packages = requests.get(self.source)
        packages.raise_for_status()
        try:
            packages_json: dict[str, Any] = packages.json()
        except requests.exceptions.JSONDecodeError as err:
            raise InvalidJSONError from err

        logger.debug("Successfully downloaded trusted packages list from %s", self.source)

        return packages_json

    @staticmethod
    def _parse(packages_info: dict[str, Any]) -> set[str]:
        try:
            names = {row["project"] for row in packages_info["rows"]}
        except KeyError as err:
            raise InvalidPyPiFormatError from err

        if not names:
            raise EmptyPackagesListError

        logger.debug("Successfully parsed trusted packages list")

        return names
