class ServerError(Exception):
    """Custom exception for HTTP 5xx errors."""


class InvalidJSONError(Exception):
    """Custom exception for when the received JSON does not match the expected format."""
