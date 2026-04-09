from twyn.base.exceptions import TwynError


class DistanceAlgorithmError(TwynError):
    """Exception raised while running distance algorithm."""

    message = "Exception raised while running distance algorithm"
    """Default error message for distance algorithm failures."""


class ThresholdError(TwynError, ValueError):
    """Exception raised when minimum threshold is greater than maximum threshold."""

    message = "Minimum threshold cannot be greater than maximum threshold."
    """Default error message for invalid threshold values."""
