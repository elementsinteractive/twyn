from unittest.mock import Mock

import pytest
from twyn.similarity.algorithm import (
    EditDistance,
    SimilarityThreshold,
)
from twyn.trusted_packages.selectors import (
    FirstLetterExact,
    FirstLetterNearbyInKeyboard,
)
from twyn.trusted_packages.trusted_packages import (
    TrustedPackages,
    TyposquatCheckResultEntry,
)


class TestTrustedPackages:
    @pytest.mark.parametrize(
        ("package_name", "is_a_trusted_package"),
        [("foo", True), ("FOO", False), ("asdf", False)],
    )
    def test_can_check_package_is_trusted(self, package_name: str, is_a_trusted_package: bool):
        trusted_packages = TrustedPackages(
            names={"foo", "bar"},
            algorithm=Mock(),
            selector=Mock(),
            threshold_class=Mock(),
        )
        assert (package_name in trusted_packages) is is_a_trusted_package

    def test_tree_representation(self):
        trusted_packages = TrustedPackages(
            names={"foo", "ffoo", "bar", "zoo"},
            algorithm=Mock(),
            selector=Mock(),
            threshold_class=Mock(),
        )
        assert trusted_packages.names == {
            "f": {"foo", "ffoo"},
            "b": {"bar"},
            "z": {"zoo"},
        }

    @pytest.mark.parametrize(
        ("package_name", "trusted_packages", "selector", "matches"),
        [
            # First letter exact
            (
                "foo",
                {"foo"},
                FirstLetterExact(),
                [],
            ),  # shares first letter, distance is 0, below threshold
            (
                "fooo",
                {"foo"},
                FirstLetterExact(),
                ["foo"],
            ),  # shares first letter, distance is 1, inside threshold
            (
                "foooo",
                {"foo"},
                FirstLetterExact(),
                [],
            ),  # shares first letter, distance is 2, above threshold
            (
                "numpy",
                {"lumpy"},
                FirstLetterExact(),
                [],
            ),  # distance is 1, inside threshold, but start with different letter
            (
                "abcdefghijklm",
                {"abcdefghijklmn"},
                FirstLetterExact(),
                ["abcdefghijklmn"],
            ),  # distance is 2, inside threshold (because it's a longer word)
            # Nearby letters
            (
                "numpy",
                {"numpy"},
                FirstLetterNearbyInKeyboard(),
                [],
            ),  # distance is 0, outside threshold.
            (
                "lumpy",
                {"numpy"},
                FirstLetterNearbyInKeyboard(),
                [],
            ),  # distance is 1, inside threshold. First letter is changed but not nearby
            (
                "mumpy",
                {"numpy"},
                FirstLetterNearbyInKeyboard(),
                ["numpy"],
            ),  # distance is 1, inside threshold. First letter is changed and nearby
            (
                "abcdefghijklm",
                {"sbcdefghijklm"},
                FirstLetterNearbyInKeyboard(),
                ["sbcdefghijklm"],
            ),  # distance is 2, inside threshold. First letter is changed and nearby
            (
                "rest_framework",
                {"erst_framweork"},
                FirstLetterNearbyInKeyboard(),
                ["erst_framweork"],
            ),  # distance is 2, inside threshold (cause it's a long word). First letter is changed and nearby.
        ],
    )
    def test_get_typosquat(self, package_name, trusted_packages, selector, matches):
        trusted_packages = TrustedPackages(
            names=trusted_packages,
            algorithm=EditDistance(),
            selector=selector,
            threshold_class=SimilarityThreshold,
        )

        assert trusted_packages.get_typosquat(package_name=package_name) == TyposquatCheckResultEntry(
            dependency=package_name, similars=matches
        )
