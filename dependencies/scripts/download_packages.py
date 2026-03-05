import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import click
import httpx
import stamina
from requests.exceptions import InvalidJSONError

from scripts.exceptions import ServerError
from scripts.utils import (
    DEPENDENCIES_DIR,
    ECOSYSTEMS,
    RETRY_ATTEMPTS,
    RETRY_ON,
    RETRY_WAIT_EXP_BASE,
    RETRY_WAIT_JITTER,
    RETRY_WAIT_MAX,
    TIMEOUT,
)

logger = logging.getLogger("weekly_download")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


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
