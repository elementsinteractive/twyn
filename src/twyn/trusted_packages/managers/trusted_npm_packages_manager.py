from collections import defaultdict
from typing import Any

from twyn.similarity.algorithm import (
    AbstractSimilarityAlgorithm,
    SimilarityThreshold,
)
from twyn.trusted_packages.managers.base import OrderedPackages
from twyn.trusted_packages.models import TyposquatCheckResultEntry
from twyn.trusted_packages.selectors import AbstractSelector


class TrustedNpmPackageManager:
    """Representation of namespaces that can be trusted."""

    def __init__(
        self,
        names: set[str],
        algorithm: AbstractSimilarityAlgorithm,
        selector: AbstractSelector,
        threshold_class: type[SimilarityThreshold],
    ) -> None:
        self.packages, self.namespaces = self._create_names_dictionary(names)

        self.threshold_class = threshold_class
        self.selector = selector
        self.algorithm = algorithm

    def __contains__(self, obj: Any) -> bool:
        """Check if an object exists in the trusted namespaces."""
        if isinstance(obj, str):
            return obj in self.packages[obj[0]] or obj in self.namespaces
        return False

    def _create_names_dictionary(self, names: set[str]) -> tuple[OrderedPackages, OrderedPackages]:
        """Create a dictionary which will group all packages that start with the same letter under the same key."""
        first_letter_names: OrderedPackages = defaultdict(set)
        namespaces: OrderedPackages = defaultdict(set)
        for name in names:
            if name.startswith("@"):
                namespace, dependency = name.split("/")
                namespaces[namespace].add(dependency)
            else:
                first_letter_names[name[0]].add(name)
        return first_letter_names, namespaces

    def _get_typosquats_from_namespace_dependency(self, package_name: str) -> TyposquatCheckResultEntry:
        namespace, dependency = package_name.split("/")
        threshold = self.threshold_class.from_name(namespace)
        typosquat_result = TyposquatCheckResultEntry(dependency=package_name)
        for trusted_namespace_name in self.selector.select_similar_names(
            names={"@": self.namespaces.keys()}, name=namespace
        ):
            distance = self.algorithm.get_distance(namespace, trusted_namespace_name)
            if threshold.is_inside_threshold(distance) and dependency in self.namespaces[trusted_namespace_name]:
                typosquat_result.add(f"{trusted_namespace_name}/{dependency}")
        return typosquat_result

    def _get_typosquats_from_dependency(self, package_name: str) -> TyposquatCheckResultEntry:
        threshold = self.threshold_class.from_name(package_name)
        typosquat_result = TyposquatCheckResultEntry(dependency=package_name)
        for trusted_package_name in self.selector.select_similar_names(names=self.packages, name=package_name):
            distance = self.algorithm.get_distance(package_name, trusted_package_name)
            if threshold.is_inside_threshold(distance):
                typosquat_result.add(trusted_package_name)
        return typosquat_result

    def get_typosquat(self, package_name: str) -> TyposquatCheckResultEntry:
        """Check if a given package name is similar to any trusted package and returns it.

        Only if there is a match on the first letter can a package name be
        considered similar to another one. The algorithm provided and the threshold
        are used to determine if the package name can be considered similar.
        """
        if package_name.startswith("@"):
            return self._get_typosquats_from_namespace_dependency(package_name)
        return self._get_typosquats_from_dependency(package_name)
