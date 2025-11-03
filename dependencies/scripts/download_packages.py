import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import click
import httpx
import stamina

logger = logging.getLogger("weekly_download")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class ServerError(Exception):
    """Custom exception for HTTP 5xx errors."""


class InvalidJSONError(Exception):
    """Custom exception for when the received JSON does not match the expected format."""


# Directory name
DEPENDENCIES_DIR = "dependencies"
"""Directory name where dependency files will be saved."""

# Sources
TOP_PYPI_SOURCE = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
"""URL for fetching top PyPI packages data."""

TOP_NPM_SOURCE = "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages"
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


def parse_npm(data: list[dict[str, Any]]) -> set[str]:
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
    parser=parse_npm,
    params={"per_page": 100, "sort": "downloads"},
    pages=150,
)
"""Ecosystem configuration for npm packages with pagination."""


ECOSYSTEMS = {"pypi": pypi_ecosystem, "npm": npm_ecosystem}
"""Dictionary mapping ecosystem names to their configurations."""


def get_params(params: dict[str, Any] | None, page: int | None) -> dict[str, Any]:
    """Combine base parameters with page parameter if provided."""
    new_params: dict[str, Any] = {}
    if params:
        new_params |= params

    if page:
        new_params["page"] = page

    return new_params


def _run(ecosystem: str) -> None:
    """Download packages for the specified ecosystem and save to file."""
    selected_ecosystem = ECOSYSTEMS[ecosystem]
    all_packages: set[str] = set()

    n_pages = selected_ecosystem.pages or 1
    with httpx.Client(timeout=TIMEOUT) as client:
        for page in range(1, n_pages + 1):
            params = get_params(selected_ecosystem.params, page if selected_ecosystem.pages else None)
            all_packages.update(get_packages(client, selected_ecosystem.url, selected_ecosystem.parser, params))

    fpath = Path(DEPENDENCIES_DIR) / f"{ecosystem}.json"
    save_data_to_file(list(all_packages), fpath)


@click.group()
def entry_point() -> None:
    """Entry point for the CLI application."""
    pass


@entry_point.command()
@click.argument(
    "ecosystem",
    type=str,
    required=True,
)
def download(
    ecosystem: str,
) -> None:
    """Download packages for the specified ecosystem."""
    if ecosystem not in ECOSYSTEMS:
        raise click.BadParameter("Not a valid ecosystem")

    return _run(ecosystem)


def get_packages(
    client: httpx.Client,
    base_url: str,
    parser: Callable[[dict[str, Any]], set[str]],
    params: dict[str, Any] | None = None,
) -> set[str]:
    """Fetch and parse package data from a URL with retry logic."""
    for attempt in stamina.retry_context(
        on=RETRY_ON,
        attempts=RETRY_ATTEMPTS,
        wait_jitter=RETRY_WAIT_JITTER,
        wait_exp_base=RETRY_WAIT_EXP_BASE,
        wait_max=RETRY_WAIT_MAX,
    ):
        with attempt:
            response = client.get(str(base_url), params=params)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.is_server_error:
                    raise ServerError from e
    try:
        json_data = response.json()
    except json.JSONDecodeError as e:
        raise InvalidJSONError from e

    return parser(json_data)


def save_data_to_file(all_packages: list[str], fpath: Path) -> None:
    """Save package data to a JSON file with timestamp."""
    data = {"date": datetime.now(ZoneInfo("UTC")).isoformat(), "packages": all_packages}
    with open(str(fpath), "w") as fp:
        json.dump(data, fp)

    logger.info("Saved %d packages to `%s` file.", len(all_packages), fpath)


if __name__ == "__main__":
    entry_point()
