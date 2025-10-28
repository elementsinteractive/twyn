from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias

from twyn import dependency_parser
from twyn.trusted_packages import selectors

if TYPE_CHECKING:
    from twyn.dependency_parser.parsers.abstract_parser import AbstractParser


MANUAL_INPUT_SOURCE = "manual_input"
"""Source identifier for manually provided dependencies."""

SELECTOR_METHOD_MAPPING: dict[str, type[selectors.AbstractSelector]] = {
    "first-letter": selectors.FirstLetterExact,
    "nearby-letter": selectors.FirstLetterNearbyInKeyboard,
    "all": selectors.AllSimilar,
}
"""Mapping of selector method names to their corresponding classes."""

SELECTOR_METHOD_KEYS = set(SELECTOR_METHOD_MAPPING.keys())
"""Set of available selector method names."""

SelectorMethod = Literal["first-letter", "nearby-letter", "all"]
"""Type alias for valid selector method strings."""

DEPENDENCY_FILE_MAPPING: dict[str, type[AbstractParser]] = {
    "requirements.txt": dependency_parser.RequirementsTxtParser,
    "poetry.lock": dependency_parser.PoetryLockParser,
    "uv.lock": dependency_parser.UvLockParser,
    "package-lock.json": dependency_parser.PackageLockJsonParser,
    "yarn.lock": dependency_parser.YarnLockParser,
}
"""Mapping of dependency file names to their parser classes."""


DEFAULT_SELECTOR_METHOD = "all"
"""Default method for selecting similar packages."""

DEFAULT_PROJECT_TOML_FILE = "pyproject.toml"
"""Default filename for project configuration."""

DEFAULT_TWYN_TOML_FILE = "twyn.toml"
"""Default filename for Twyn-specific configuration."""

DEFAULT_USE_CACHE = True
"""Default setting for cache usage."""

DEFAULT_RECURSIVE = False
"""Default setting for recursive processing."""


PackageEcosystems: TypeAlias = Literal["pypi", "npm"]
"""Type alias for supported package ecosystems."""
