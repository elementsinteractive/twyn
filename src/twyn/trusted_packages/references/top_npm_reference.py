import logging
import re

from typing_extensions import override

from twyn.trusted_packages.exceptions import (
    PackageNormalizingError,
)
from twyn.trusted_packages.references.base import AbstractPackageReference, NormalizedPackages

logger = logging.getLogger("twyn")


class TopNpmReference(AbstractPackageReference):
    """Top npm packages retrieved from an online source."""

    DEFAULT_SOURCE: str = (
        "https://raw.githubusercontent.com/elementsinteractive/twyn/refs/heads/main/dependencies/npm.json"
    )
    """Default URL for fetching top npm packages."""

    @override
    @staticmethod
    def normalize_packages(packages: set[str]) -> NormalizedPackages:
        """Normalize dependency names according to npm."""
        if not packages:
            logger.debug("Tried to normalize packages, but none were provided")
            return NormalizedPackages(packages=set())

        # Extract namespaces from package names
        package_pattern = re.compile(r"^[a-z0-9-~][a-z0-9-._~]*$")  # noqa: F821
        namespace_pattern = re.compile(r"^(?:@[a-z0-9-~][a-z0-9-._~]*)\/[a-z0-9-~][a-z0-9-._~]*$")  # noqa: F821

        extracted_namespaces: dict[str, set[str]] = {}
        regular_packages = set()

        for package in packages:
            if namespace_pattern.match(package.lower()):
                namespace, namespace_package = package.split("/")
                if namespace not in extracted_namespaces:
                    extracted_namespaces[namespace] = set()
                extracted_namespaces[namespace].add(namespace_package)
            elif package_pattern.match(package.lower()):
                regular_packages.add(package)
            else:
                raise PackageNormalizingError(f"Package name '{package}' does not match required pattern")

        return NormalizedPackages(packages=regular_packages, namespaces=extracted_namespaces)
