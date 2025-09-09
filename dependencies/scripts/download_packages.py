import json
from pathlib import Path
from typing import Any

import click
import httpx
import stamina


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
@click.option(
    "--ecosystem",
    type=str,
    required=True,
    help="Package ecosystem to download packages from.",
)
def run(ecosystem: str) -> None:
    for attempt in stamina.retry_context(
        on=(
            httpx.TransportError,
            httpx.TimeoutException,
        ),
        attempts=3,
        timeout=60,
    ):
        with attempt, httpx.Client() as client:
            response = client.get(ECOSYSTEMS[ecosystem]["url"])  # type: ignore[arg-type]
        response.raise_for_status()

    fpath = Path("dependencies") / f"{ecosystem}.json"

    data = ECOSYSTEMS[ecosystem]["parser"](response.json())  # type: ignore[operator]

    with open(str(fpath), "w") as fp:
        json.dump(data, fp)


if __name__ == "__main__":
    entry_point()
