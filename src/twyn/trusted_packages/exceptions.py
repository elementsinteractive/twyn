from twyn.base.exceptions import TwynError


class InvalidJSONError(TwynError):
    """Exception raised when JSON decoding of downloaded packages list fails."""

    message = "Could not json decode the downloaded packages list"


class InvalidPyPiFormatError(TwynError):
    """Exception raised when PyPI JSON format is invalid."""

    message = "Invalid JSON format."


class EmptyPackagesListError(TwynError):
    """Exception raised when downloaded packages list is empty."""

    message = "Downloaded packages list is empty"


class CharacterNotInMatrixError(TwynError):
    """Exception raised when a character is not found in the similarity matrix."""

    message = "Character not found in similarity matrix"


class InvalidCacheError(TwynError):
    """Error for when the cache content is not valid."""

    message = "Invalid cache content"
