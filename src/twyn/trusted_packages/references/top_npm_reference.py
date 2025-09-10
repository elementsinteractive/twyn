import logging
import re

from typing_extensions import override

from twyn.trusted_packages.exceptions import (
    PackageNormalizingError,
)
from twyn.trusted_packages.references.base import AbstractPackageReference

logger = logging.getLogger("twyn")


class TopNpmReference(AbstractPackageReference):
    """Top npm packages retrieved from an online source."""

    DEFAULT_SOURCE: str = (
        "https://raw.githubusercontent.com/elementsinteractive/twyn/refs/heads/main/dependencies/npm.json"
    )

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
