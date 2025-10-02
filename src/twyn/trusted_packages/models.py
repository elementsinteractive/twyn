from typing import Optional

from pydantic import BaseModel


class TyposquatCheckResultEntry(BaseModel):
    """Represents the result of analyzing a dependency for a possible typosquat."""

    dependency: str
    """Name of the dependency being checked."""
    similars: list[str] = []
    """List of similar package names that might be typosquats."""

    def __bool__(self) -> bool:
        """Check if this result entry contains any similar packages."""
        return bool(self.similars)

    def add(self, similar_name: str) -> None:
        """Add a similar dependency to this typosquat check result."""
        self.similars.append(similar_name)


class TyposquatCheckResultFromSource(BaseModel):
    errors: list[TyposquatCheckResultEntry] = []
    """List of typosquat check result entries."""
    source: str
    """Source identifier for the dependency file or input."""

    def __bool__(self) -> bool:
        """Check if this result contains any errors."""
        return bool(self.errors)

    def __contains__(self, value: TyposquatCheckResultEntry) -> bool:
        """Check if the given entry is in the errors list."""
        if not isinstance(value, TyposquatCheckResultEntry):
            return False
        return value in self.errors

    def get_typosquats(self) -> set[str]:
        """Return a set containing all the detected packages with a typo."""
        return {typo.dependency for typo in self.errors}


class TyposquatCheckResults(BaseModel):
    results: list[TyposquatCheckResultFromSource] = []
    """List of typosquat check results from different sources."""

    def __bool__(self) -> bool:
        """Check if this result collection contains any results."""
        return bool(self.results)

    def get_results_from_source(self, source: str) -> Optional[TyposquatCheckResultFromSource]:
        """Return results from a given source.

        Source is either the lock file that has been analyzed or `manual_input`.
        """
        for result in self.results:
            if result.source == source:
                return result
