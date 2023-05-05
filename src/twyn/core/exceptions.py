from twyn.base.exceptions import TwynError


class AllowlistError(TwynError):
    def __init__(self, package_name: str = ""):
        message = self.message.format(package_name) if package_name else self.message
        super().__init__(message)


class AllowlistPackageAlreadyExistsError(AllowlistError):
    message = "Package '{}' is already present in the allowlist. Skipping."


class AllowlistPackageDoesNotExistError(AllowlistError):
    message = "Package '{}' is not present in the allowlist. Skipping."
