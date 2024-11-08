from twyn.base.exceptions import TwynError


class PathIsNotFileError(TwynError):
    message = "Specified dependencies path is not a file"


class PathNotFoundError(TwynError, FileNotFoundError):
    message = "Specified dependencies file path does not exist"
