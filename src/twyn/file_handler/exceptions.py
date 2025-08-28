from twyn.base.exceptions import TwynError


class PathIsNotFileError(TwynError):
    """Exception raised when a specified path exists but is not a regular file."""

    message = "Specified dependencies path is not a file"


class PathNotFoundError(TwynError):
    """Exception raised when a specified file path does not exist in the filesystem."""

    message = "Specified dependencies file path does not exist"
