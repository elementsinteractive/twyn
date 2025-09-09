from twyn.base.exceptions import TwynError


class InvalidFileFormatError(TwynError):
    """Exception raised when a lock file does not match the expected format."""

    message = "Unknown format found while reading file."
