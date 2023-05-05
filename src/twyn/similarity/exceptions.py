from twyn.base.exceptions import TwynError


class DistanceAlgorithmError(TwynError):
    message = "Exception raised while running distance algorithm"


class ThresholdError(TwynError, ValueError):
    message = "Minimum threshold cannot be greater than maximum threshold."
