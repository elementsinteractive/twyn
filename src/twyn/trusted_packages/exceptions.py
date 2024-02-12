from twyn.base.exceptions import TwynError


class InvalidJSONError(TwynError):
    message = "Could not json decode the downloaded packages list"


class InvalidPyPiFormatError(TwynError, KeyError):
    message = "Invalid JSON format."


class EmptyPackagesListError(TwynError):
    message = "Downloaded packages list is empty"


class CharacterNotInMatrixError(TwynError, KeyError): ...
