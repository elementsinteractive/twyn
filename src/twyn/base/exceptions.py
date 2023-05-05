class TwynError(Exception):
    message = ""

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.message)
