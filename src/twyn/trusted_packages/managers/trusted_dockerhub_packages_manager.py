import logging
from collections import defaultdict
from typing import Any

from twyn.similarity.algorithm import (
    AbstractSimilarityAlgorithm,
    SimilarityThreshold,
)
from twyn.trusted_packages.managers.base import OrderedPackages
from twyn.trusted_packages.models import TyposquatCheckResultEntry
from twyn.trusted_packages.selectors import AbstractSelector

logger = logging.getLogger("twyn")


class TrustedDockerHubPackageManager:
    """Representation of namespaces that can be trusted."""

    def __init__(
        self,
        names: set[str],
        algorithm: AbstractSimilarityAlgorithm,
        selector: AbstractSelector,
        threshold_class: type[SimilarityThreshold],
    ) -> None:
        self.namespaces = self._create_names_dictionary(names)

        self.threshold_class = threshold_class
        self.selector = selector
        self.algorithm = algorithm

    def __contains__(self, obj: Any) -> bool:
        """Check if an object exists in the trusted namespaces."""
        if isinstance(obj, str):
            return obj in self.namespaces
        return False

    def get_typosquat(self, package_name: str) -> TyposquatCheckResultEntry:
        """Check if a given package name is similar to any trusted package and returns it.

        Only if there is a match on the first letter can a package name be
        considered similar to another one. The algorithm provided and the threshold
        are used to determine if the package name can be considered similar.
        """
        if "/" not in package_name:
            logger.info(
                "`%s` is an image from the official Docker registry, will be skipped.",
                package_name,
            )
            return

        registry_parts = package_name.split("/")
        namespace = "/".join(registry_parts[:-1])
        image_path = registry_parts[-1]
        typosquat_result = TyposquatCheckResultEntry(dependency=package_name)
        threshold = self.threshold_class.from_name(namespace)
        for trusted_namespace_name in self.selector.select_similar_names(
            names={"@": self.namespaces.keys()}, name=namespace
        ):
            distance = self.algorithm.get_distance(namespace, trusted_namespace_name)

            if threshold.is_inside_threshold(distance) and image_path in self.namespaces[trusted_namespace_name]:
                typosquat_result.add(f"{trusted_namespace_name}/{image_path}")
        return typosquat_result

    def _create_names_dictionary(self, names: set[str]) -> OrderedPackages:
        """Create a dictionary which will group all packages that start with the same letter under the same key."""
        namespaces: OrderedPackages = defaultdict(set)
        for name in names:
            registry = name.split("/")
            namespaces["/".join(registry[:-1])].add(registry[-1])

        return namespaces
