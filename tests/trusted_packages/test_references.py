from contextlib import contextmanager
from unittest.mock import Mock, call, patch

import pytest
import requests
from pyparsing import Iterable, Iterator
from twyn.trusted_packages import TopPyPiReference
from twyn.trusted_packages.exceptions import (
    EmptyPackagesListError,
    InvalidJSONError,
    InvalidPyPiFormatError,
)
from twyn.trusted_packages.references import AbstractPackageReference


@contextmanager
def patch_pypi_requests_get(packages: Iterable[str]) -> Iterator[Mock]:
    """Patcher of `requests.get` for Top PyPi list.

    Replaces call with the output you would get from downloading the top PyPi packages list.
    """
    json_response = {"rows": [{"project": name} for name in packages]}

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = json_response

        yield mock_get


class TestAbstractPackageReference:
    class HardcodedPackageReference(AbstractPackageReference):
        """Returns always the same packages, used for testing the interface."""

        def get_packages(self) -> set[str]:
            return {"foo", "bar"}

    def test_get_packages(self):
        assert self.HardcodedPackageReference().get_packages() == {"foo", "bar"}


class TestTopPyPiReference:
    @patch_pypi_requests_get(packages=["boto3", "urllib3", "requests"])
    def test_get_trusted_packages(self):
        top_pypi = TopPyPiReference(source="foo")

        assert top_pypi.get_packages() == {"boto3", "urllib3", "requests"}

    def test__parse_no_rows(self):
        data = {"bananas": 5}
        top_pypi = TopPyPiReference(source="foo")

        with pytest.raises(InvalidPyPiFormatError, match="Invalid JSON format."):
            top_pypi._parse(data)

    def test_empty_packages_list_exception(self):
        with pytest.raises(
            EmptyPackagesListError,
            match="Downloaded packages list is empty",
        ):
            TopPyPiReference._parse({"rows": []})

    def test__parse_retrieves_package_names(self):
        data = {"rows": [{"project": "boto3"}, {"project": "requests"}]}
        top_pypi = TopPyPiReference(source="foo")

        assert top_pypi._parse(data) == {"boto3", "requests"}

    @pytest.mark.parametrize("source", ["foo.com", "bar.com"])
    def test_can_use_different_pypi_sources(self, source):
        top_pypi = TopPyPiReference(source=source)

        with patch_pypi_requests_get(packages=["foo"]) as mock_get:
            top_pypi.get_packages()

        assert mock_get.call_args_list == [call(source)]

    @patch("requests.get")
    def test__download_json_exception(self, mock_get):
        mock_get.return_value.json.side_effect = requests.exceptions.JSONDecodeError(
            "This exception will be mapped and never shown", "", 1
        )
        top_pypi = TopPyPiReference(source="foo")

        with pytest.raises(
            InvalidJSONError,
            match="Could not json decode the downloaded packages list",
        ):
            top_pypi._download()

    @patch_pypi_requests_get(packages=["boto3", "requests"])
    def test__download(self):
        top_pypi = TopPyPiReference(source="foo")

        assert top_pypi._download() == {
            "rows": [
                {"project": "boto3"},
                {"project": "requests"},
            ]
        }
