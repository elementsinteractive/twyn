import logging
import re

from typing_extensions import override

from twyn.trusted_packages.exceptions import (
    PackageNormalizingError,
)
from twyn.trusted_packages.references.base import AbstractPackageReference, NormalizedPackages

logger = logging.getLogger("twyn")


class TopDockerHubReference(AbstractPackageReference):
    """Top npm packages retrieved from an online source."""

    DEFAULT_SOURCE: str = (
        "https://raw.githubusercontent.com/elementsinteractive/twyn/refs/heads/main/dependencies/dockerhub.json"
    )
    """Default URL for fetching top DockerHub packages."""

    @override
    @staticmethod
    def normalize_packages(packages: set[str]) -> NormalizedPackages:
        """Normalize dependency names according to DockerHub."""
        if not packages:
            logger.debug("Tried to normalize packages, but none were provided")
            return NormalizedPackages(packages=set())

        # Extract namespaces from package names
        # Updated patterns to handle Docker registry URLs and complex namespaces
        package_pattern = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")  # noqa: F821
        # Pattern for namespaced packages (registry/namespace/image or namespace/image)
        # Allows dots, dashes, underscores in registry/namespace names
        namespace_pattern = re.compile(r"^[a-z0-9._-]+(?:/[a-z0-9._-]+)*$")  # noqa: F821

        extracted_namespaces: dict[str, set[str]] = {}
        regular_packages = set()

        for package in packages:
            if "/" in package and namespace_pattern.match(package.lower()):
                # For namespaced packages, use the last component as package name
                # and everything before it as namespace
                parts = package.split("/")
                if len(parts) >= 2:
                    namespace = "/".join(parts[:-1])  # Everything except last part
                    namespace_package = parts[-1]  # Last part is the package name
                    if namespace not in extracted_namespaces:
                        extracted_namespaces[namespace] = set()
                    extracted_namespaces[namespace].add(namespace_package)
                else:
                    regular_packages.add(package)
            elif package_pattern.match(package.lower()):
                regular_packages.add(package)
            else:
                raise PackageNormalizingError(f"Package name '{package}' does not match required pattern")

        return NormalizedPackages(packages=regular_packages, namespaces=extracted_namespaces)
