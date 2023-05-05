from __future__ import annotations

import enum
from typing import TYPE_CHECKING

import twyn.dependency_parser as dependency_parser
from twyn.trusted_packages import selectors

if TYPE_CHECKING:
    from twyn.dependency_parser.abstract_parser import AbstractParser

SELECTOR_METHOD_MAPPING: dict[str, type[selectors.AbstractSelector]] = {
    "first-letter": selectors.FirstLetterExact,
    "nearby-letter": selectors.FirstLetterNearbyInKeyboard,
    "all": selectors.AllSimilar,
}

DEPENDENCY_FILE_MAPPING: dict[str, type[AbstractParser]] = {
    "requirements.txt": dependency_parser.requirements_txt.RequirementsTxtParser,
    "poetry.lock": dependency_parser.poetry_lock.PoetryLockParser,
}

DEFAULT_SELECTOR_METHOD = "all"
DEFAULT_DEPENDENCY_FILE = "requirements.txt"
DEFAULT_PROJECT_TOML_FILE = "pyproject.toml"


class AvailableLoggingLevels(enum.Enum):
    none = "NONE"
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
