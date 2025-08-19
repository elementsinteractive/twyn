from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from twyn import dependency_parser
from twyn.trusted_packages import selectors

if TYPE_CHECKING:
    from twyn.dependency_parser.abstract_parser import AbstractParser


SELECTOR_METHOD_MAPPING: dict[str, type[selectors.AbstractSelector]] = {
    "first-letter": selectors.FirstLetterExact,
    "nearby-letter": selectors.FirstLetterNearbyInKeyboard,
    "all": selectors.AllSimilar,
}

DEPENDENCY_FILE_MAPPING: dict[str, type[AbstractParser]] = {
    "requirements.txt": dependency_parser.requirements_txt_parser.RequirementsTxtParser,
    "poetry.lock": dependency_parser.lock_parser.PoetryLockParser,
    "uv.lock": dependency_parser.lock_parser.UvLockParser,
}

DEFAULT_SELECTOR_METHOD = "all"
DEFAULT_PROJECT_TOML_FILE = "pyproject.toml"
DEFAULT_TOP_PYPI_PACKAGES = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"


class AvailableLoggingLevels(enum.Enum):
    none = "NONE"
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
