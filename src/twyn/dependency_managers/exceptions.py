from twyn.base.exceptions import TwynError


class NoMatchingDependencyManagerError(TwynError):
    """Error for when a DependencyManger cannot be retrieved based on the provided arguments."""
