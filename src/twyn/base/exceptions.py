import logging
from typing import IO, Any, Optional

import click

logger = logging.getLogger("twyn.errors")


class TwynError(Exception):
    """
    Base exception from where all application errors will inherit.

    Provides a default message field, that subclasses will override to provide more information in case it is not provided during the exception handling.
    """

    message = ""

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.message)


class CliError(click.ClickException):
    """Error that will populate application errors to stdout. It does not inherit from `TwynError`."""

    message = "CLI error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)

    def show(self, file: Optional[IO[Any]] = None) -> None:
        logger.debug(self.format_message(), exc_info=True)
        logger.error(self.format_message(), exc_info=False)


class PackageNormalizingError(TwynError):
    """Exception for when it is not possible to normalize a package name."""

    message = "Failed to normalize pacakges."
