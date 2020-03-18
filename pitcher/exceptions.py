from typing import Optional


class APIException(Exception):
    status_code = 500
    default_message = "Internal server error"

    def __init__(
        self, message: Optional[str] = None, code: Optional[int] = None
    ) -> None:
        if message is None:
            message = self.default_message
        self.message = message

        if code is not None:
            self.status_code = code


class BadRequest(APIException):
    status_code = 400
    default_message = "Bad Request"


class NotFound(APIException):
    status_code = 404
    default_message = "Not Found"


class MethodNotAllowed(APIException):
    status_code = 405
    default_message = "Method Not Allowed"
