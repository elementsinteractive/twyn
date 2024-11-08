from twyn.base.exceptions import TwynError


class NoMatchingParserError(TwynError):
    message = "Could not assign a dependency file parser. Please specify it with --dependency-file"


class MultipleParsersError(TwynError):
    message = "Can't auto detect dependencies file to parse. More than one format was found."
