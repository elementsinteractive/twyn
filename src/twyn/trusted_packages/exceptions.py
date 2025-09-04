from twyn.base.exceptions import TwynError


class InvalidJSONError(TwynError):
    """Exception raised when JSON decoding of downloaded packages list fails."""

    message = "Could not json decode the downloaded packages list"


class InvalidReferenceFormatError(TwynError):
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


class PackageNormalizingError(TwynError):
    """Exception for when it is not possible to normalize a package name."""

    message = "Failed to normalize pacakges."


class InvalidSelectorMethodError(TwynError):
    """Exception raised when an invalid selector method is provided."""

    message = "Invalid selector method specified."


class InvalidArgumentsError(TwynError):
    """Exception raised when invalid arguments are passed to a function or method."""

    message = "Invalid arguments provided."
