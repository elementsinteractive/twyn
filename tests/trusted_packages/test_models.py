import pytest
from pydantic import ValidationError
from twyn.trusted_packages.models import (
    TyposquatCheckResultEntry,
    TyposquatCheckResultFromSource,
    TyposquatCheckResults,
)


class TestModels:
    def test_typosquat_check_result_entry_bool_and_add(self) -> None:
        entry = TyposquatCheckResultEntry(dependency="left-pad")
        assert not entry  # __bool__ should be False if no similars
        entry.add("leftpad")
        assert entry  # __bool__ should be True if similars exist
        assert entry.similars == ["leftpad"]

    def test_typosquat_check_result_entry_validation(self) -> None:
        with pytest.raises(ValidationError):
            TyposquatCheckResultEntry(dependency=None)

    def test_typosquat_check_result_from_source_bool_contains_get_typosquats(self) -> None:
        entry1 = TyposquatCheckResultEntry(dependency="foo", similars=["fou"])
        entry2 = TyposquatCheckResultEntry(dependency="baz", similars=["bar"])
        result = TyposquatCheckResultFromSource(errors=[entry1, entry2], source="npm")
        assert result  # __bool__ should be True if any entry is True
        assert entry1 in result
        assert entry2 in result
        assert result.get_typosquats() == {"foo", "baz"}

    def test_typosquat_check_result_from_source_empty(self) -> None:
        result = TyposquatCheckResultFromSource(errors=[], source="npm")
        assert not result
        assert result.get_typosquats() == set()

    def test_typosquat_check_results_bool(self) -> None:
        entry = TyposquatCheckResultEntry(dependency="foo", similars=["bar"])
        result = TyposquatCheckResultFromSource(errors=[entry], source="npm")
        results = TyposquatCheckResults(results=[result])
        assert results
        empty_results = TyposquatCheckResults(results=[])
        assert not empty_results

    def test_typosquat_check_results_from_source(self) -> None:
        entry = TyposquatCheckResultEntry(dependency="foo", similars=["bar"])
        result = TyposquatCheckResultFromSource(errors=[entry], source="npm")
        results = TyposquatCheckResults(results=[result])

        assert results.get_results_from_source("npm") == result
        assert results.get_results_from_source("pypi") is None
