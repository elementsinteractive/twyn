"""Dependency parsers."""

from twyn.dependency_parser.lock_parser import PoetryLockParser, UvLockParser
from twyn.dependency_parser.requirements_txt_parser import RequirementsTxtParser

__all__ = ["RequirementsTxtParser", "PoetryLockParser", "UvLockParser"]
