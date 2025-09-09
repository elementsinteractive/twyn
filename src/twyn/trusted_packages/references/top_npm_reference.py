import logging
import re
from typing import Any

from typing_extensions import override

from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidReferenceFormatError,
    PackageNormalizingError,
)
from twyn.trusted_packages.references.base import AbstractPackageReference

logger = logging.getLogger("twyn")


class TopNpmReference(AbstractPackageReference):
    """Top npm packages retrieved from an online source."""

    DEFAULT_SOURCE: str = "https://www.npmleaderboard.org/api/packages"

    @override
    @staticmethod
    def _parse(packages_info: dict[str, Any]) -> set[str]:
        try:
            names = {pkg["name"] for pkg in packages_info["packages"]}

        except KeyError as err:
            raise InvalidReferenceFormatError from err

        if not names:
            raise EmptyPackagesListError

        logger.debug("Successfully parsed trusted packages list")
        return names

    @override
    @staticmethod
    def normalize_packages(packages: set[str]) -> set[str]:
        """Normalize dependency names according to npm."""
        if not packages:
            logger.debug("Tried to normalize packages, but none were provided")
            return set()

        pattern = re.compile(r"^(?:@[a-z0-9-~][a-z0-9-._~]*\/)?[a-z0-9-~][a-z0-9-._~]*$")  # noqa: F821
        for package in packages:
            if not pattern.match(package.lower()):
                raise PackageNormalizingError(f"Package name '{package}' does not match required pattern")

        return packages
