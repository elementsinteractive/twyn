from collections import defaultdict
from typing import Any, Protocol

from twyn.trusted_packages.models import TyposquatCheckResultEntry

OrderedPackages = defaultdict[str, set[str]]
"""Type alias for mapping package names by ecosystem."""


class TrustedPackagesProtocol(Protocol):
    def __contains__(self, obj: Any) -> bool: ...

    def get_typosquat(self, package_name: str) -> TyposquatCheckResultEntry: ...
