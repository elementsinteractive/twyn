from twyn.base.exceptions import TwynError


class TOMLError(TwynError):
    """TOML exception class."""

    message = "TOML parsing error"

    def __init__(self, message: str):
        super().__init__(message)


class BaseAllowlistError(TwynError):
    """Base `allowlist` exception."""

    message = "Allowlist error"

    def __init__(self, package_name: str = "") -> None:
        message = self.message.format(package_name) if package_name else self.message
        super().__init__(message)


class AllowlistPackageAlreadyExistsError(BaseAllowlistError):
    """Exception class for when a package already exists in the allowlist."""

    message = "Package '{}' is already present in the allowlist. Skipping."


class AllowlistPackageDoesNotExistError(BaseAllowlistError):
    """Exception class for when it is not possible to locate the desired pacakge in the allowlist."""

    message = "Package '{}' is not present in the allowlist. Skipping."


class InvalidSelectorMethodError(TwynError):
    """Exception for when an invalid selector method has been specified."""

    message = "Invalid `Selector` was provided."
