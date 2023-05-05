from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Set

from twyn.similarity.algorithm import (
    AbstractSimilarityAlgorithm,
    SimilarityThreshold,
)
from twyn.trusted_packages.selectors import AbstractSelector

_PackageNames = defaultdict[str, set[str]]


@dataclass
class TyposquatCheckResult:
    """Represents the result of analyzing a dependency for a possible typosquat."""

    candidate_dependency: str
    similar_dependencies: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.similar_dependencies)

    def add(self, similar_name: str) -> None:
        """Add a similar dependency to this typosquat check result."""
        self.similar_dependencies.append(similar_name)


class TrustedPackages:
    """Representation of packages that can be trusted."""

    def __init__(
        self,
        names: Set[str],
        algorithm: AbstractSimilarityAlgorithm,
        selector: AbstractSelector,
        threshold_class: type[SimilarityThreshold],
    ) -> None:
        self.names: _PackageNames = self._create_names_dictionary(names)
        self.threshold_class = threshold_class
        self.selector = selector
        self.algorithm = algorithm

    def __eq__(self, obj: Any) -> bool:
        return isinstance(obj, self.__class__) and self.names == obj.names

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
        typosquat_result = TyposquatCheckResult(package_name)
        for trusted_package_name in self.selector.select_similar_names(
            names=self.names, name=package_name
        ):
            distance = self.algorithm.get_distance(package_name, trusted_package_name)
            if threshold.is_inside_threshold(distance):
                typosquat_result.add(trusted_package_name)
        return typosquat_result
