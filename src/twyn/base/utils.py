import re


def _normalize_packages(packages: set[str]) -> set[str]:
    """Normalize dependency names according to PyPi https://packaging.python.org/en/latest/specifications/name-normalization/."""
    return {re.sub(r"[-_.]+", "-", name).lower() for name in packages}
