import sys

import click

from twyn.__version__ import __version__
from twyn.base.constants import (
    DEPENDENCY_FILE_MAPPING,
    SELECTOR_METHOD_MAPPING,
    AvailableLoggingLevels,
)
from twyn.core.config_handler import ConfigHandler
from twyn.main import check_dependencies


@click.group()
@click.version_option(__version__, "--version")
def entry_point() -> None:
    pass


@entry_point.command()
@click.option("--config", type=click.STRING)
@click.option(
    "--dependency-file",
    type=click.Choice(list(DEPENDENCY_FILE_MAPPING.keys())),
    help=(
        "Dependency file to analyze. By default, twyn will search in the current directory "
        "for supported files, but this option will override that behavior."
    ),
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
def run(
    config: str,
    dependency_file: str,
    selector_method: str,
    v: bool,
    vv: bool,
) -> int:
    if v and vv:
        raise ValueError(
            "Only one verbosity level is allowed. Choose either -v or -vv."
        )

    if v:
        verbosity = AvailableLoggingLevels.info
    elif vv:
        verbosity = AvailableLoggingLevels.debug
    else:
        verbosity = AvailableLoggingLevels.none

    return int(
        check_dependencies(
            config_file=config,
            dependency_file=dependency_file,
            selector_method=selector_method,
            verbosity=verbosity,
        )
    )


@entry_point.group()
def allowlist() -> None:
    pass


@allowlist.command()
@click.argument("package_name")
def add(package_name: str) -> None:
    ConfigHandler().add_package_to_allowlist(package_name)


@allowlist.command()
@click.argument("package_name")
def remove(package_name: str) -> None:
    ConfigHandler().remove_package_from_allowlist(package_name)


if __name__ == "__main__":
    sys.exit(entry_point())
