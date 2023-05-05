import pytest
from twyn.trusted_packages.exceptions import CharacterNotInMatrixError
from twyn.trusted_packages.selectors import (
    AllSimilar,
    FirstLetterExact,
    FirstLetterNearbyInKeyboard,
)

NAMES = {"f": {"foo", "ffoo"}, "b": {"bar"}, "z": {"zoo"}, "d": {"dellows"}}


class TestFirstLetterExact:
    def test_select_similar_names(self):
        selector = FirstLetterExact()
        assert set(selector.select_similar_names(NAMES, "fellows")) == {
            "foo",
            "ffoo",
        }


class TestFirstLetterNearbyInKeyboard:
    def test_select_similar_names(self):
        selector = FirstLetterNearbyInKeyboard()
        assert set(selector.select_similar_names(NAMES, "fellows")) == {
            "foo",
            "ffoo",
            "dellows",
        }

    def test__get_candidate_characters(self):
        assert FirstLetterNearbyInKeyboard._get_candidate_characters("c") == [
            "d",
            "f",
            "x",
            "v",
            "c",
        ]

    def test_character_not_in_matrix(self):
        with pytest.raises(
            CharacterNotInMatrixError,
            match="Character '.' not supported",
        ):
            FirstLetterNearbyInKeyboard._get_candidate_characters(".")


class TestAllSimilar:
    def test_select_similar_names(self):
        selector = AllSimilar()
        assert set(selector.select_similar_names(NAMES, "fellows")) == {
            "foo",
            "ffoo",
            "dellows",
            "bar",
            "zoo",
        }
