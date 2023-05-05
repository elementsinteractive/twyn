from twyn.base.exceptions import TwynError


class PathIsNotFileError(TwynError):
    message = "Specified dependencies path is not a file"


class PathNotFoundError(TwynError, FileNotFoundError):
    message = "Specified dependencies file path does not exist"


class NoMatchingParserError(TwynError):
    message = "Could not assign a dependency file parser. Please specify it with --dependency-file"


class MultipleParsersError(TwynError):
    message = (
        "Can't auto detect dependencies file to parse. More than one format was found."
    )
