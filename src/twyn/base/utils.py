import re

from twyn.base.exceptions import PackageNormalizingError


def normalize_packages(packages: set[str]) -> set[str]:
    """Normalize dependency names according to PyPi https://packaging.python.org/en/latest/specifications/name-normalization/."""
    renamed_packages = {re.sub(r"[-_.]+", "-", name).lower() for name in packages}

    pattern = re.compile(r"^([a-z0-9]|[a-z0-9][a-z0-9._-]*[a-z0-9])\Z")
    for package in renamed_packages:
        if not pattern.match(package):
            raise PackageNormalizingError(f"Package name '{package}' does not match required pattern")

    return renamed_packages
