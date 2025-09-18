import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
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


def parse_npm(data: list[dict[str, Any]]) -> list[str]:
    return [x["name"] for x in data]


def parse_pypi(data: dict[str, Any]) -> list[str]:
    return [row["project"] for row in data["rows"]]


class ServerError(Exception):
    """Custom exception for HTTP 5xx errors."""


@dataclass(frozen=True)
class Ecosystem:
    url: str
    params: Optional[dict[str, Any]]
    pages: Optional[int]
    parser: Callable[[dict[str, Any]], list[str]]


@dataclass(frozen=True)
class PypiEcosystem(Ecosystem):
    url = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
    params = None
    pages = None
    parser = parse_pypi


@dataclass(frozen=True)
class NpmEcosystem(Ecosystem):
    url = "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages"
    params = {"per_page": 1000, "sort": "downloads"}
    pages = 15
    parser = parse_npm


ECOSYSTEMS = {"pypi": PypiEcosystem, "npm": NpmEcosystem}


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
    selected_ecosystem = ECOSYSTEMS[ecosystem]

    if pages := selected_ecosystem.pages:
        all_packages: list[str] = []

        for page in range(1, pages + 1):
            params = selected_ecosystem.params or {}
            params["page"] = page
            all_packages.extend(get_packages(selected_ecosystem.url, selected_ecosystem.parser, params))
    else:
        all_packages = get_packages(selected_ecosystem.url, selected_ecosystem.parser, selected_ecosystem.params)

    fpath = Path("dependencies") / f"{ecosystem}.json"
    save_data_to_file(all_packages, fpath)


def get_packages(
    base_url: str, parser: Callable[[dict[str, Any]], list[str]], params: Optional[dict[str, Any]] = None
) -> list[str]:
    for attempt in stamina.retry_context(
        on=(httpx.TransportError, httpx.TimeoutException, ServerError),
        attempts=5,
        wait_jitter=1,
        wait_exp_base=2,
        wait_max=8,
    ):
        with attempt, httpx.Client(timeout=30) as client:
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

    logger.info("Saved %d packages to `%s` file.", len(set(all_packages)), fpath)


if __name__ == "__main__":
    entry_point()
