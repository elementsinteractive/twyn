from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from typing_extensions import TypeAlias

from twyn import dependency_parser
from twyn.trusted_packages import selectors

if TYPE_CHECKING:
    from twyn.dependency_parser.parsers.abstract_parser import AbstractParser


MANUAL_INPUT_SOURCE = "manual_input"

SELECTOR_METHOD_MAPPING: dict[str, type[selectors.AbstractSelector]] = {
    "first-letter": selectors.FirstLetterExact,
    "nearby-letter": selectors.FirstLetterNearbyInKeyboard,
    "all": selectors.AllSimilar,
}

SELECTOR_METHOD_KEYS = set(SELECTOR_METHOD_MAPPING.keys())
SelectorMethod = Literal["first-letter", "nearby-letter", "all"]

DEPENDENCY_FILE_MAPPING: dict[str, type[AbstractParser]] = {
    "requirements.txt": dependency_parser.RequirementsTxtParser,
    "poetry.lock": dependency_parser.PoetryLockParser,
    "uv.lock": dependency_parser.UvLockParser,
    "package-lock.json": dependency_parser.PackageLockJsonParser,
    "yarn.lock": dependency_parser.YarnLockParser,
}


DEFAULT_SELECTOR_METHOD = "all"
DEFAULT_PROJECT_TOML_FILE = "pyproject.toml"
DEFAULT_TWYN_TOML_FILE = "twyn.toml"
DEFAULT_USE_CACHE = True


PackageEcosystems: TypeAlias = Literal["pypi", "npm"]
