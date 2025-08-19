from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from rapidfuzz.distance import DamerauLevenshtein

from twyn.similarity.exceptions import DistanceAlgorithmError, ThresholdError

logger = logging.getLogger("twyn")


class SimilarityThreshold:
    LENGTH_CUTOFF = 5
    MIN_VALUE = 1.0
    MAX_FOR_SHORT_WORDS = 1.0
    MAX_FOR_LONG_WORDS = 2.0

    def __init__(self, max: float) -> None:
        self.min = self.MIN_VALUE
        self.max = max

        if self.min > self.max:
            raise ThresholdError

    @classmethod
    def from_name(cls, name: str) -> SimilarityThreshold:
        name_length = len(name)
        if name_length <= cls.LENGTH_CUTOFF:
            logger.debug("max length of %s selected for %s", cls.MAX_FOR_SHORT_WORDS, name)
            return cls(max=cls.MAX_FOR_SHORT_WORDS)
        logger.debug("max length of {cls.MAX_FOR_LONG_WORDS} selected for %s", name)
        return cls(max=cls.MAX_FOR_LONG_WORDS)  # we allow more typos if the name is longer

    def is_inside_threshold(self, value: float) -> bool:
        return self.min <= value <= self.max


class AbstractSimilarityAlgorithm(ABC):
    """Algorithm that can compare sequences based of a particular similarity measure."""

    def get_distance(self, first_sequence: str, second_sequence: str) -> float | int:
        """
        Perform the alignment between sequences and return the computed distance.

        Will raise DistanceAlgorithmError if an exception occurs.
        """
        try:
            return self._run_algorithm(first_sequence, second_sequence)
        except Exception as exc:
            raise DistanceAlgorithmError from exc

    @abstractmethod
    def _run_algorithm(self, first_sequence: str, second_sequence: str) -> float | int:
        """Abstract method that runs the selected algorithm for computing the distance between two words."""


class EditDistance(AbstractSimilarityAlgorithm):
    """Levenshtein algorithm that computes the edit distance between words."""

    def _run_algorithm(self, first_sequence: str, second_sequence: str) -> int:
        return DamerauLevenshtein.distance(s1=first_sequence, s2=second_sequence)
