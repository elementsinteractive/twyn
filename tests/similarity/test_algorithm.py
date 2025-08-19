from typing import Union

import pytest
from twyn.similarity.algorithm import (
    AbstractSimilarityAlgorithm,
    EditDistance,
    SimilarityThreshold,
)
from twyn.similarity.exceptions import DistanceAlgorithmError, ThresholdError


class TestAbstractSimilarityAlgorithm:
    class DifferentLettersSimilarityAlgorithm(AbstractSimilarityAlgorithm):
        def _run_algorithm(self, first_sequence: str, second_sequence: str) -> Union[float, int]:
            first_letters = set(first_sequence)
            second_letters = set(second_sequence)
            return len(first_letters.symmetric_difference(second_letters))

    @pytest.mark.parametrize(
        (
            "word1",
            "word2",
            "expected_distance",
        ),
        [
            ("foo", "bar", 5),
            ("foo", "foo", 0),
            ("foo", "fooo", 0),
            ("foo", "boo", 2),
        ],
    )
    def test_distance_between_words(self, word1, word2, expected_distance):
        algorithm = self.DifferentLettersSimilarityAlgorithm()
        assert algorithm.get_distance(word1, word2) == expected_distance


class TestEditDistance:
    @pytest.mark.parametrize(
        (
            "word1",
            "word2",
            "expected_distance",
        ),
        [
            ("requests", "requests", 0),
            ("requests", "requets", 1),
            ("reque", "requests", 3),
        ],
    )
    def test_distance_between_words(self, word1, word2, expected_distance):
        algorithm = EditDistance()
        assert algorithm.get_distance(word1, word2) == expected_distance


class TestExceptions:
    class ExceptionAlgorithm(AbstractSimilarityAlgorithm):
        def _run_algorithm(self, first_sequence: str, second_sequence: str) -> Union[float, int]:
            raise KeyError

    def test_exception(self):
        with pytest.raises(
            DistanceAlgorithmError,
            match="Exception raised while running distance algorithm",
        ):
            self.ExceptionAlgorithm().get_distance("", "")


class TestSimilarityThreshold:
    def test_invalid_threshold(self):
        with pytest.raises(ThresholdError):
            SimilarityThreshold(max=0)
