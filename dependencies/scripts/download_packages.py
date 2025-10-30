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


DEPENDENCIES_DIR = "dependencies"
TOP_PYPI_SOURCE = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
TOP_NPM_SOURCE = "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages"
TIMEOUT = 90


def parse_npm(data: list[dict[str, Any]]) -> set[str]:
    return {x["name"] for x in data}


def parse_pypi(data: dict[str, Any]) -> set[str]:
    return {row["project"] for row in data["rows"]}


class ServerError(Exception):
    """Custom exception for HTTP 5xx errors."""


@dataclass(frozen=True)
class Ecosystem:
    url: str
    parser: Callable[[Any], set[str]]
    params: dict[str, Any] = field(default_factory=dict)
    pages: int | None = None


pypi_ecosystem = Ecosystem(
    url=TOP_PYPI_SOURCE,
    parser=parse_pypi,
)

npm_ecosystem = Ecosystem(
    url=TOP_NPM_SOURCE,
    parser=parse_npm,
    params={"per_page": 100, "sort": "downloads"},
    pages=150,
)


ECOSYSTEMS = {"pypi": pypi_ecosystem, "npm": npm_ecosystem}


@click.group()
def entry_point() -> None:
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
    if ecosystem not in ECOSYSTEMS:
        raise click.BadParameter("Not a valid ecosystem")

    selected_ecosystem = ECOSYSTEMS[ecosystem]
    all_packages: set[str] = set()

    n_pages = selected_ecosystem.pages or 1
    params = selected_ecosystem.params.copy()
    for page in range(1, n_pages + 1):
        if selected_ecosystem.pages:
            params["page"] = page

        all_packages.update(get_packages(selected_ecosystem.url, selected_ecosystem.parser, params))

    fpath = Path(DEPENDENCIES_DIR) / f"{ecosystem}.json"
    save_data_to_file(list(all_packages), fpath)


@stamina.retry(
    on=(httpx.TransportError, httpx.TimeoutException, ServerError),
    attempts=10,
    wait_jitter=1,
    wait_exp_base=2,
    wait_max=8,
)
def get_packages(
    base_url: str, parser: Callable[[dict[str, Any]], set[str]], params: dict[str, Any] | None = None
) -> set[str]:
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(str(base_url), params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.is_server_error:
                raise ServerError from e
    return parser(response.json())


def save_data_to_file(all_packages: list[str], fpath: Path) -> None:
    data = {"date": datetime.now(ZoneInfo("UTC")).isoformat(), "packages": all_packages}
    with open(str(fpath), "w") as fp:
        json.dump(data, fp)

    logger.info("Saved %d packages to `%s` file.", len(all_packages), fpath)


if __name__ == "__main__":
    entry_point()
