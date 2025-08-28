import logging
import sys
from typing import Optional

import click
from rich.logging import RichHandler

from twyn.__version__ import __version__
from twyn.base.constants import (
    DEFAULT_PROJECT_TOML_FILE,
    DEPENDENCY_FILE_MAPPING,
    SELECTOR_METHOD_MAPPING,
    AvailableLoggingLevels,
)
from twyn.base.exceptions import CliError, TwynError
from twyn.config.config_handler import ConfigHandler
from twyn.file_handler.file_handler import FileHandler
from twyn.main import check_dependencies
from twyn.trusted_packages.cache_handler import CacheHandler
from twyn.trusted_packages.constants import CACHE_DIR

logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
logger = logging.getLogger("twyn")


@click.group()
@click.version_option(__version__, "--version")
def entry_point() -> None:
    pass


@entry_point.command()
@click.option("--config", type=click.STRING)
@click.option(
    "--dependency-file",
    type=str,
    help=(
        "Dependency file to analyze. By default, twyn will search in the current directory "
        "for supported files, but this option will override that behavior."
    ),
)
@click.option(
    "--dependency",
    type=str,
    multiple=True,
    help="Dependency to analyze. Cannot be set together with --dependency-file. If provided, it will take precedence over the default dependency file.",
)
@click.option(
    "--selector-method",
    type=click.Choice(list(SELECTOR_METHOD_MAPPING.keys())),
    help=(
        "Which method twyn should use to select possible typosquats. "
        "`first-letter` only compares dependencies that share the first letter, "
        "while `nearby-letter` compares against dependencies whose first letter "
        "is nearby in an English keyboard. `all` compares the given dependencies "
        "against all of those in the reference."
    ),
)
@click.option(
    "-v",
    default=False,
    is_flag=True,
)
@click.option(
    "-vv",
    default=False,
    is_flag=True,
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable use of the trusted packages cache. Always fetch from the source.",
)
def run(
    config: str,
    dependency_file: Optional[str],
    dependency: tuple[str],
    selector_method: str,
    v: bool,
    vv: bool,
    no_cache: bool,
) -> int:
    if v and vv:
        raise click.UsageError(
            "Only one verbosity level is allowed. Choose either -v or -vv.", ctx=click.get_current_context()
        )

    if v:
        verbosity = AvailableLoggingLevels.info
    elif vv:
        verbosity = AvailableLoggingLevels.debug
    else:
        verbosity = AvailableLoggingLevels.none

    if dependency and dependency_file:
        raise click.UsageError(
            "Only one of --dependency or --dependency-file can be set at a time.", ctx=click.get_current_context()
        )

    if dependency_file and not any(dependency_file.endswith(key) for key in DEPENDENCY_FILE_MAPPING):
        raise click.UsageError("Dependency file name not supported.", ctx=click.get_current_context())

    try:
        errors = check_dependencies(
            dependencies=set(dependency) or None,
            config_file=config,
            dependency_file=dependency_file,
            selector_method=selector_method,
            verbosity=verbosity,
            use_cache=not no_cache,
        )
    except TwynError as e:
        raise CliError(e.message) from e
    except Exception as e:
        raise CliError("Unhandled exception occured.") from e

    if errors:
        for possible_typosquats in errors:
            click.echo(
                click.style("Possible typosquat detected: ", fg="red")
                + f"`{possible_typosquats.candidate_dependency}`, "
                f"did you mean any of [{', '.join(possible_typosquats.similar_dependencies)}]?",
                color=True,
            )
        sys.exit(1)
    else:
        click.echo(click.style("No typosquats detected", fg="green"), color=True)
        sys.exit(0)


@entry_point.group()
def allowlist() -> None:
    pass


@allowlist.command()
@click.option("--config", type=click.STRING)
@click.argument("package_name")
def add(package_name: str, config: str) -> None:
    fh = FileHandler(config or DEFAULT_PROJECT_TOML_FILE)
    ConfigHandler(fh).add_package_to_allowlist(package_name)


@allowlist.command()
@click.option("--config", type=click.STRING)
@click.argument("package_name")
def remove(package_name: str, config: str) -> None:
    fh = FileHandler(config or DEFAULT_PROJECT_TOML_FILE)
    ConfigHandler(fh).remove_package_from_allowlist(package_name)


@entry_point.group()
def cache() -> None:
    pass


@cache.command()
def clear() -> None:
    """Clear cached trusted packages data."""
    cache_handler = CacheHandler(CACHE_DIR)

    cache_handler.clear_all()
    click.echo(click.style("All cache cleared", fg="green"))


if __name__ == "__main__":
    sys.exit(entry_point())
