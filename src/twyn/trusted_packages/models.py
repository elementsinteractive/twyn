from typing import Optional

from pydantic import BaseModel


class TyposquatCheckResultEntry(BaseModel):
    """Represents the result of analyzing a dependency for a possible typosquat."""

    dependency: str
    similars: list[str] = []

    def __bool__(self) -> bool:
        return bool(self.similars)

    def add(self, similar_name: str) -> None:
        """Add a similar dependency to this typosquat check result."""
        self.similars.append(similar_name)


class TyposquatCheckResultFromSource(BaseModel):
    errors: list[TyposquatCheckResultEntry] = []
    source: str

    def __bool__(self) -> bool:
        return bool(self.errors)

    def __contains__(self, value: TyposquatCheckResultEntry) -> bool:
        if not isinstance(value, TyposquatCheckResultEntry):
            return False
        return value in self.errors

    def get_typosquats(self) -> set[str]:
        """Return a set containing all the detected packages with a typo."""
        return {typo.dependency for typo in self.errors}


class TyposquatCheckResults(BaseModel):
    results: list[TyposquatCheckResultFromSource] = []

    def __bool__(self) -> bool:
        return bool(self.results)

    def get_results_from_source(self, source: str) -> Optional[TyposquatCheckResultFromSource]:
        """Return results from a given source.

        Source is either the lock file that has been analyzed or `manual_input`.
        """
        for result in self.results:
            if result.source == source:
                return result
