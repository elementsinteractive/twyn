import sys
from typing import Optional

import click

from twyn.__version__ import __version__
from twyn.base.constants import (
    DEFAULT_PROJECT_TOML_FILE,
    DEPENDENCY_FILE_MAPPING,
    SELECTOR_METHOD_MAPPING,
    AvailableLoggingLevels,
)
from twyn.config.config_handler import ConfigHandler
from twyn.file_handler.file_handler import FileHandler
from twyn.main import check_dependencies


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
def run(
    config: str,
    dependency_file: Optional[str],
    dependency: tuple[str],
    selector_method: str,
    v: bool,
    vv: bool,
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

    return int(
        check_dependencies(
            config_file=config,
            dependency_file=dependency_file,
            dependencies_cli=set(dependency) or None,
            selector_method=selector_method,
            verbosity=verbosity,
        )
    )


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


if __name__ == "__main__":
    sys.exit(entry_point())
