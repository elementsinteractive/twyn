from collections import defaultdict
from typing import Any

from pydantic import BaseModel

from twyn.similarity.algorithm import (
    AbstractSimilarityAlgorithm,
    SimilarityThreshold,
)
from twyn.trusted_packages.selectors import AbstractSelector

_PackageNames = defaultdict[str, set[str]]


class TyposquatCheckResult(BaseModel):
    """Represents the result of analyzing a dependency for a possible typosquat."""

    dependency: str
    similars: list[str] = []

    def __bool__(self) -> bool:
        return bool(self.similars)

    def add(self, similar_name: str) -> None:
        """Add a similar dependency to this typosquat check result."""
        self.similars.append(similar_name)


class TyposquatCheckResultList(BaseModel):
    errors: list[TyposquatCheckResult] = []

    def get_typosquats(self) -> set[str]:
        """Return a set containing all the detected packages with a typo."""
        return {typo.dependency for typo in self.errors}


class TrustedPackages:
    """Representation of packages that can be trusted."""

    def __init__(
        self,
        names: set[str],
        algorithm: AbstractSimilarityAlgorithm,
        selector: AbstractSelector,
        threshold_class: type[SimilarityThreshold],
    ) -> None:
        self.names: _PackageNames = self._create_names_dictionary(names)
        self.threshold_class = threshold_class
        self.selector = selector
        self.algorithm = algorithm

    def __contains__(self, obj: Any) -> bool:
        if isinstance(obj, str):
            return obj in self.names[obj[0]]
        return False

    @staticmethod
    def _create_names_dictionary(names: set[str]) -> _PackageNames:
        """Create a dictionary which will group all packages that start with the same letter under the same key."""
        first_letter_names = defaultdict(set)
        for name in names:
            first_letter_names[name[0]].add(name)
        return first_letter_names

    def get_typosquat(
        self,
        package_name: str,
    ) -> TyposquatCheckResult:
        """Check if a given package name is similar to any trusted package and returns it.

        Only if there is a match on the first letter can a package name be
        considered similar to another one. The algorithm provided and the threshold
        are used to determine if the package name can be considered similar.
        """
        threshold = self.threshold_class.from_name(package_name)
        typosquat_result = TyposquatCheckResult(dependency=package_name)
        for trusted_package_name in self.selector.select_similar_names(names=self.names, name=package_name):
            distance = self.algorithm.get_distance(package_name, trusted_package_name)
            if threshold.is_inside_threshold(distance):
                typosquat_result.add(trusted_package_name)
        return typosquat_result
