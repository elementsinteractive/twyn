"""Dependency parsers."""

from twyn.dependency_parser.poetry_lock import PoetryLockParser
from twyn.dependency_parser.requirements_txt import RequirementsTxtParser

__all__ = ["RequirementsTxtParser", "PoetryLockParser"]
