import logging
import re

from typing_extensions import override

from twyn.trusted_packages.exceptions import (
    PackageNormalizingError,
)
from twyn.trusted_packages.references.base import AbstractPackageReference

logger = logging.getLogger("twyn")


class TopPyPiReference(AbstractPackageReference):
    """Top PyPi packages retrieved from an online source."""

    DEFAULT_SOURCE: str = (
        "https://raw.githubusercontent.com/elementsinteractive/twyn/refs/heads/main/dependencies/pypi.json"
    )
    """Default URL for fetching top PyPI packages."""

    @override
    @staticmethod
    def normalize_packages(packages: set[str]) -> set[str]:
        """Normalize dependency names according to PyPi https://packaging.python.org/en/latest/specifications/name-normalization/."""
        if not packages:
            logger.debug("Tried to normalize packages, but none were provided")
            return set()
        renamed_packages = {re.sub(r"[-_.]+", "-", name).lower() for name in packages}

        pattern = re.compile(r"^([a-z0-9]|[a-z0-9][a-z0-9._-]*[a-z0-9])\Z")  # noqa: F821
        for package in renamed_packages:
            if not pattern.match(package):
                raise PackageNormalizingError(f"Package name '{package}' does not match required pattern")

        return renamed_packages
