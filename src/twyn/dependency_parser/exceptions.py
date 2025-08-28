from twyn.base.exceptions import TwynError


class NoMatchingParserError(TwynError):
    """Exception raised when no suitable dependency file parser can be automatically determined."""

    message = "Could not assign a dependency file parser. Please specify it with --dependency-file"


class MultipleParsersError(TwynError):
    """Exception raised when multiple dependency file parsers are detected."""

    message = "Can't auto detect dependencies file to parse. More than one format was found."
