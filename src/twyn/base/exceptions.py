import logging
from typing import IO, Any, Optional

import click

logger = logging.getLogger("twyn.errors")


class TwynError(click.ClickException):
    message = ""

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.message)

    def show(self, file: Optional[IO[Any]] = None) -> None:
        logger.debug(self.format_message(), exc_info=True)
        logger.error(self.format_message(), exc_info=False)


class PackageNormalizingError(TwynError):
    """Exception for when it is not possible to normalize a package name."""
