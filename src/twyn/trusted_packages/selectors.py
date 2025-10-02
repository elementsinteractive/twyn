from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from twyn.trusted_packages.constants import ADJACENCY_MATRIX
from twyn.trusted_packages.exceptions import CharacterNotInMatrixError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from twyn.trusted_packages.trusted_packages import _PackageNames

logger = logging.getLogger("twyn")


class AbstractSelector(ABC):
    @abstractmethod
    def select_similar_names(self, names: _PackageNames, name: str) -> Iterable[str]:
        """Override this to select names that are similar to the provided one."""

    def __str__(self) -> str:
        """Return the class name as string representation."""
        return self.__class__.__name__


class FirstLetterNearbyInKeyboard(AbstractSelector):
    """Selects names that start with a letter that is nearby in an English Keyboard."""

    def select_similar_names(self, names: _PackageNames, name: str) -> Iterable[str]:
        """Select package names with first letters nearby on keyboard."""
        candidate_characters = self._get_candidate_characters(name[0])
        for letter in candidate_characters:
            yield from names.get(letter, [])

    @staticmethod
    def _get_candidate_characters(character: str) -> list[str]:
        """Get keyboard adjacent characters for the given character."""
        if character not in ADJACENCY_MATRIX:
            raise CharacterNotInMatrixError(f"Character '{character}' not supported")

        return ADJACENCY_MATRIX[character] + [character]


class FirstLetterExact(AbstractSelector):
    """Selects names that share the same first letter."""

    def select_similar_names(self, names: _PackageNames, name: str) -> Iterable[str]:
        """Select package names that start with the same letter."""
        yield from names[name[0]]


class AllSimilar(AbstractSelector):
    """Consider all names to be similar."""

    def select_similar_names(self, names: _PackageNames, name: str) -> Iterable[str]:
        """Return all available package names as candidates."""
        for candidates in names.values():
            yield from candidates
