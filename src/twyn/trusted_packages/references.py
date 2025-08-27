import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import requests

from twyn.base.utils import normalize_packages
from twyn.trusted_packages.cache_handler import CacheEntry, CacheHandler
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
    InvalidPyPiFormatError,
)

logger = logging.getLogger("twyn")


class AbstractPackageReference(ABC):
    """Represents a reference from where to retrieve trusted packages."""

    def __init__(self, source: str, cache_handler: CacheHandler) -> None:
        self.source = source
        self.cache_handler = cache_handler

    @abstractmethod
    def get_packages(self, use_cache: bool = True) -> set[str]:
        """Return the names of the trusted packages available in the reference."""


class TopPyPiReference(AbstractPackageReference):
    """Top PyPi packages retrieved from an online source."""

    def get_packages(self, use_cache: bool = True) -> set[str]:
        """Download and parse online source of top Python Package Index packages."""
        packages_to_use = set()
        if use_cache:
            packages_to_use = self._get_packages_from_cache()
            # we don't save the cache here, we keep it as it is so the date remains the original one.

        if not packages_to_use:
            # no cache usage, no cache hit (non-existent or outdated) or cache was empty.
            logger.info("Fetching trusted packages from PyPI reference...")
            packages_to_use = self._parse(self._download())
            if use_cache:
                self._save_trusted_packages_to_cache(packages_to_use)

        normalized_packages = normalize_packages(packages_to_use)
        return normalized_packages

    def _save_trusted_packages_to_cache(self, packages: set[str]) -> None:
        """Save trusted packages using CacheHandler."""
        cache_entry = CacheEntry(saved_date=datetime.now().date().isoformat(), packages=packages)
        self.cache_handler.write_entry(self.source, cache_entry)
        logger.debug("Saved %d trusted packages for source %s", len(packages), self.source)

    def _get_packages_from_cache(self) -> set[str]:
        """Get packages from cache if it's present and up to date."""
        cache_entry = self.cache_handler.get_cache_entry(self.source)
        if not cache_entry:
            logger.debug("No cache entry found for source: %s", self.source)
            return set()

        return cache_entry.packages

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
