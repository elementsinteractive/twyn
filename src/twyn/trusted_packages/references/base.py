import logging
from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests

from twyn.trusted_packages.cache_handler import CacheEntry, CacheHandler
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
)

logger = logging.getLogger("twyn")


@dataclass
class NormalizedPackages:
    packages: set[str]
    namespaces: dict[str, set[str]] | None = None
    _raw_namespaces: set[str] = field(default_factory=set)

    def __post__init__(self) -> None:
        if self.namespaces:
            for namespace in self.namespaces:
                for package_name in self.namespaces[namespace]:
                    self._raw_namespaces.add(f"{namespace}/{package_name}")

    def __iter__(self) -> Iterator[str]:
        yield from self.packages

        if not self.namespaces:
            return

        for namespace in self.namespaces:
            for package_name in self.namespaces[namespace]:
                yield f"{namespace}/{package_name}"

    def __contains__(self, value: str) -> bool:
        if not isinstance(value, str):
            return False

        return value in self.packages or value in self._raw_namespaces


class AbstractPackageReference:
    """Represents a reference from where to retrieve trusted packages.

    It abstracts all the package-retrieval and caching logic.

    It defines the `_parse` abstract method, so each subclass defines how to handle the feched data.
    It defines the `normalize_package` abstract method, so each subclass validates that the packages names are correct.
    """

    DEFAULT_SOURCE: str
    """Default URL source for fetching trusted packages."""

    def __init__(self, source: str | None = None, cache_handler: CacheHandler | None = None) -> None:
        self.source = source or self.DEFAULT_SOURCE
        self.cache_handler = cache_handler

    @staticmethod
    @abstractmethod
    def normalize_packages(packages: set[str]) -> NormalizedPackages:
        """Normalize package names to make sure they're valid within the package manager context."""

    def _download(self) -> dict[str, Any]:
        """Download data from the source URL."""
        response = requests.get(self.source)
        response.raise_for_status()

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as err:
            raise InvalidJSONError from err

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

    def get_packages(self) -> NormalizedPackages:
        """Download and parse online source of top packages from the package ecosystem."""
        packages = self._get_packages_from_cache_if_enabled()
        # we don't save the cache here, we keep it as it is so the date remains the original one.
        if not packages:
            # no cache usage, no cache hit (non-existent or outdated) or cache was empty.
            logger.info("Fetching trusted packages from trusted packages reference...")
            data = self._download()
            try:
                packages = set(data["packages"])
            except KeyError as err:
                raise InvalidJSONError("`packages` key not in JSON.") from err

            logger.debug("Successfully downloaded trusted packages list from %s", self.source)
            if not packages:
                raise EmptyPackagesListError

            # New packages were downloaded, we create a new entry updating all values.
            self._save_trusted_packages_to_cache_if_enabled(packages)

        return self.normalize_packages(packages)
