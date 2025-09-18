from twyn.base.exceptions import TwynError


class NoMatchingDependencyManagerError(TwynError):
    """Error for when a DependencyManger cannot be retrieved based on the provided arguments."""


class MultipleSourcesError(TwynError):
    """Error for when more than one alternative source matches the configuration."""
