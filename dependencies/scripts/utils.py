from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from requests.exceptions import InvalidJSONError

from scripts.exceptions import ServerError

DEPENDENCIES_DIR = "dependencies"
"""Directory name where dependency files will be saved."""

# Sources
TOP_PYPI_SOURCE = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
"""URL for fetching top PyPI packages data."""

TOP_NPM_SOURCE = "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages"
"""URL for fetching top npm packages data from ecosyste.ms."""

TOP_DOCKERHUB_SOURCE = "https://packages.ecosyste.ms/api/v1/registries/hub.docker.com/packages"
"""URL for fetching top npm packages data from ecosyste.ms."""

# Retry constants
RETRY_ON = (httpx.TransportError, httpx.TimeoutException, ServerError)
"""Tuple of exceptions that should trigger retry attempts."""

RETRY_ATTEMPTS = 15
"""Maximum number of retry attempts for failed requests."""

RETRY_WAIT_JITTER = 1
"""Random jitter factor for retry wait times."""

RETRY_WAIT_EXP_BASE = 2
"""Exponential backoff base multiplier for retry wait times."""

RETRY_WAIT_MAX = 8
"""Maximum wait time between retry attempts in seconds."""

TIMEOUT = 90
"""HTTP request timeout in seconds."""


def parse_packages_ecosystems_source(data: list[dict[str, Any]]) -> set[str]:
    """Parse npm package data and extract package names."""
    try:
        return {x["name"] for x in data}
    except KeyError as e:
        raise InvalidJSONError from e


def parse_pypi(data: dict[str, Any]) -> set[str]:
    """Parse PyPI package data and extract package names."""
    try:
        return {row["project"] for row in data["rows"]}
    except KeyError as e:
        raise InvalidJSONError from e


@dataclass(frozen=True)
class Ecosystem:
    """Configuration for a package ecosystem (PyPI, npm, etc.)."""

    url: str
    parser: Callable[[Any], set[str]]
    params: dict[str, Any] = field(default_factory=dict)
    pages: int | None = None


pypi_ecosystem = Ecosystem(
    url=TOP_PYPI_SOURCE,
    parser=parse_pypi,
)
"""Ecosystem configuration for PyPI packages."""

npm_ecosystem = Ecosystem(
    url=TOP_NPM_SOURCE,
    parser=parse_packages_ecosystems_source,
    params={"per_page": 100, "sort": "downloads"},
    pages=150,
)
"""Ecosystem configuration for npm packages with pagination."""

dockerhub_ecosystem = Ecosystem(
    url=TOP_DOCKERHUB_SOURCE,
    parser=parse_packages_ecosystems_source,
    params={"per_page": 100, "sort": "downloads"},
    pages=150,
)
"""Ecosystem configuration for DockerHub packages with pagination."""


ECOSYSTEMS = {"pypi": pypi_ecosystem, "npm": npm_ecosystem, "dockerhub": dockerhub_ecosystem}
"""Dictionary mapping ecosystem names to their configurations."""
