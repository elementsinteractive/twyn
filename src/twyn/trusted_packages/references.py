import logging
from abc import ABC, abstractmethod
from typing import Any

import requests

from twyn.trusted_packages.constants import TOP_PYPI_PACKAGES, Url
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
    InvalidPyPiFormatError,
)

logger = logging.getLogger()


class AbstractPackageReference(ABC):
    """Represents a reference to retrieve trusted packages from."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @abstractmethod
    def get_packages(self) -> set[str]:
        """Return the names of the trusted packages available in the reference."""


class TopPyPiReference(AbstractPackageReference):
    """Top PyPi packages retrieved from an online source."""

    def __init__(
        self, source: Url = TOP_PYPI_PACKAGES, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.source = source

    def get_packages(self) -> set[str]:
        """Download and parse online source of top Python Package Index packages."""
        packages_info = self._download()
        return self._parse(packages_info)

    def _download(self) -> dict[str, Any]:
        packages = requests.get(self.source)
        packages.raise_for_status()
        try:
            packages_json: dict[str, Any] = packages.json()
        except requests.exceptions.JSONDecodeError as err:
            raise InvalidJSONError from err

        logger.debug(
            f"Successfully downloaded trusted packages list from {self.source}"
        )

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
