import json
import logging
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


def parse_npm(data: list[dict[str, Any]]) -> list[str]:
    return [x["name"] for x in data]


def parse_pypi(data: dict[str, Any]) -> list[str]:
    return [row["project"] for row in data["rows"]]


ECOSYSTEMS = {
    "npm": {
        "url": "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages?per_page=10000&page=1&sort=downloads",
        "parser": parse_npm,
    },
    "pypi": {
        "url": "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json",
        "parser": parse_pypi,
    },
}


@click.group()
def entry_point() -> None:
    pass


@entry_point.command()
@click.argument(
    "ecosystem",
    type=str,
    required=True,
)
def download(ecosystem: str) -> None:
    for attempt in stamina.retry_context(
        on=(
            httpx.TransportError,
            httpx.TimeoutException,
        ),
        attempts=3,
        wait_jitter=1,
        wait_exp_base=2,
        wait_max=8,
    ):
        with attempt, httpx.Client(timeout=30) as client:
            logger.info("Attempting to download %s packages. Attempt #%d.", ecosystem, attempt.num)
            response = client.get(ECOSYSTEMS[ecosystem]["url"])
            response.raise_for_status()

    fpath = Path("dependencies") / f"{ecosystem}.json"

    packages = ECOSYSTEMS[ecosystem]["parser"](response.json())  # type: ignore[operator]
    data = {"date": datetime.now(ZoneInfo("UTC")).isoformat(), "packages": packages}
    with open(str(fpath), "w") as fp:
        json.dump(data, fp)

    logger.info("Saved `%s` file.", fpath)


if __name__ == "__main__":
    entry_point()
