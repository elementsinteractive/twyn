import logging
import re
from abc import abstractmethod
from datetime import datetime
from typing import Any, Union

import requests
from typing_extensions import override

from twyn.trusted_packages.cache_handler import CacheEntry, CacheHandler
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
    InvalidPyPiFormatError,
    PackageNormalizingError,
)

logger = logging.getLogger("twyn")


class AbstractPackageReference:
    """Represents a reference from where to retrieve trusted packages.

    It abstracts all the package-retrieval and caching logic.

    It defines the `_parse` abstract method, so each subclass defines how to handle the feched data.
    It defines the `normalize_package` abstract method, so each subclass validates that the packages names are correct.
    """

    def __init__(self, source: str, cache_handler: Union[CacheHandler, None] = None) -> None:
        self.source = source
        self.cache_handler = cache_handler

    @staticmethod
    @abstractmethod
    def _parse(packages_json: dict[str, Any]) -> set[str]:
        """Parse and retrieve the packages within the given json structure."""

    @staticmethod
    @abstractmethod
    def normalize_packages(packages: set[str]) -> set[str]:
        """Normalize package names to make sure they're valid within the package manager context."""

    def _download(self) -> dict[str, Any]:
        packages = requests.get(self.source)
        packages.raise_for_status()
        try:
            packages_json: dict[str, Any] = packages.json()
        except requests.exceptions.JSONDecodeError as err:
            raise InvalidJSONError from err
        else:
            logger.debug("Successfully downloaded trusted packages list from %s", self.source)
            return packages_json

    def _save_trusted_packages_to_cache_if_enabled(self, packages: set[str]) -> None:
        """Save trusted packages using CacheHandler."""
        if not self.cache_handler:
            return
        cache_entry = CacheEntry(saved_date=datetime.now().date().isoformat(), packages=packages)
        self.cache_handler.write_entry(self.source, cache_entry)
        logger.debug("Saved %d trusted packages for source %s", len(packages), self.source)

    def _get_packages_from_cache_if_enabled(self) -> set[str]:
        """Get packages from cache if it's present and up to date."""
        if not self.cache_handler:
            return set()
        cache_entry = self.cache_handler.get_cache_entry(self.source)
        if not cache_entry:
            logger.debug("No cache entry found for source: %s", self.source)
            return set()

        return cache_entry.packages

    def get_packages(self) -> set[str]:
        """Download and parse online source of top Python Package Index packages."""
        packages_to_use = set()
        packages_to_use = self._get_packages_from_cache_if_enabled()
        # we don't save the cache here, we keep it as it is so the date remains the original one.

        if not packages_to_use:
            # no cache usage, no cache hit (non-existent or outdated) or cache was empty.
            logger.info("Fetching trusted packages from PyPI reference...")
            packages_to_use = self._parse(self._download())

            # New packages were downloaded, we create a new entry updating all values.
            self._save_trusted_packages_to_cache_if_enabled(packages_to_use)

        normalized_packages = self.normalize_packages(packages_to_use)
        return normalized_packages


class TopPyPiReference(AbstractPackageReference):
    """Top PyPi packages retrieved from an online source."""

    @override
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

    @override
    @staticmethod
    def normalize_packages(packages: set[str]) -> set[str]:
        """Normalize dependency names according to PyPi https://packaging.python.org/en/latest/specifications/name-normalization/."""
        renamed_packages = {re.sub(r"[-_.]+", "-", name).lower() for name in packages}

        pattern = re.compile(r"^([a-z0-9]|[a-z0-9][a-z0-9._-]*[a-z0-9])\Z")  # noqa: F821
        for package in renamed_packages:
            if not pattern.match(package):
                raise PackageNormalizingError(f"Package name '{package}' does not match required pattern")

        return renamed_packages
