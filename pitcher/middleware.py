from dataclasses import dataclass
import logging
from typing import Any, Callable, Iterator, List, Optional, Sequence, Union

from .request import Request
from .response import PlainTextResponse, Response
from .exceptions import BadRequest

logger = logging.getLogger()

ALL_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]


class Middleware:
    def __init__(self, cls: type, **options: Any) -> None:
        self.cls = cls
        self.options = options

    def __iter__(self) -> Iterator:
        return iter((self.cls, self.options))


class BaseMiddleware:
    def __init__(self, next_func: Callable[[Request, Any], Response],) -> None:
        self.next_func = next_func

    def __call__(self, request: Request, app: Any) -> Response:
        return self.next_func(request, app)


class CORSMiddleware(BaseMiddleware):
    def __init__(
        self,
        next_func: Callable[[Request, Any], Response],
        allow_origins: Sequence[str] = [],
        allow_methods: Sequence[str] = ["GET"],
        allow_headers: Sequence[str] = [],
        allow_credentials: bool = False,
        max_age: int = 600,
    ) -> None:
        super().__init__(next_func)

        if "*" in allow_methods:
            allow_methods = ALL_METHODS

        simple_headers = {"Access-Control-Allow-Methods": ", ".join(allow_methods)}
        if "*" in allow_origins:
            simple_headers["Access-Control-Allow-Origin"] = "*"
        if allow_credentials:
            simple_headers["Access-Control-Allow-Credentials"] = "true"

        preflight_headers = {
            "Access-Control-Allow-Methods": ", ".join(allow_methods),
            "Access-Control-Max-Age": str(max_age),
        }

        if "*" in allow_origins:
            preflight_headers["Access-Control-Allow-Origin"] = "*"
        else:
            preflight_headers["Vary"] = "Origin"

        if allow_headers and "*" not in allow_headers:
            preflight_headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)

        if allow_credentials:
            preflight_headers["Access-Control-Allow-Credentials"] = "true"

        self.allow_origins = allow_origins
        self.allow_headers = allow_headers
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods
        self.max_age = max_age
        self.simple_headers = simple_headers
        self.preflight_headers = preflight_headers

    def __call__(self, request: Request, app: Any) -> Response:
        response: Response

        origin = request.headers.get("origin")
        if request.method == "OPTIONS" and origin is not None:
            errors = []
            headers = dict(self.preflight_headers)

            requested_method = request.headers.get(
                "Access-Control-Request-Method", "GET"
            )
            if str(requested_method).upper() not in self.allow_methods:
                errors.append("method")

            if origin not in self.allow_origins and "*" not in self.allow_origins:
                headers["Access-Control-Allow-Origin"] = ", ".join(self.allow_origins)
                errors.append("origin")
            else:
                headers["Access-Control-Allow-Origin"] = origin

            if errors:
                response = PlainTextResponse(
                    400, "CORS ERROR: " + ", ".join(errors), headers=headers
                )
            else:
                response = PlainTextResponse(200, "OK", headers=headers)

            return response

        response = super().__call__(request, app)

        if origin is not None:
            response._headers.update(self.simple_headers)
            if origin in self.allow_origins:
                response._headers["Access-Control-Allow-Origin"] = origin
                response.vary("Origin")

        return response


class AllowedHostMiddleware(BaseMiddleware):
    def __init__(
        self, next_func: Callable[[Request, Any], Response], allowed_hosts: List[str],
    ) -> None:
        super().__init__(next_func)

        if "*" in allowed_hosts:
            logger.warning(
                "AllowedHostMiddleware with allowed hosts containing '*'. Disable middleware if any host is allowed"
            )

        self.allowed_hosts = allowed_hosts

    def __call__(self, request: Request, app: Any) -> Response:
        request_host = request.headers.get("host", "").split(":")[0]

        valid_host = False
        for allowed_host in self.allowed_hosts:
            if allowed_host == "*":
                valid_host = True
                break
            elif (
                request_host == allowed_host
                or allowed_host.startswith("*.")
                and request_host.endswith(allowed_host[2:])
            ):
                valid_host = True
                break

        if not valid_host:
            raise BadRequest()

        response = super().__call__(request, app)
        return response


class SecureHeadersMiddleware(BaseMiddleware):
    @dataclass
    class Header:
        __slots__ = ["header", "value"]
        header: str
        value: str

    def __init__(
        self,
        next_func: Callable[[Request, Any], Response],
        hsts: Optional[Union[bool, str]] = True,
        xss: Optional[Union[bool, str]] = True,
        content_type: Optional[Union[bool, str]] = True,
        csp: Optional[Union[bool, str]] = False,
        referrer: Optional[Union[bool, str]] = True,
    ) -> None:
        super().__init__(next_func)

        hsts_header = SecureHeadersMiddleware.Header(
            "Strict-Transport-Security", "max-age=2592000; includeSubdomains"
        )
        x_xss_protection = SecureHeadersMiddleware.Header(
            "X-XSS-Protection", "1; mode=block"
        )
        x_content_type_options = SecureHeadersMiddleware.Header(
            "X-Content-Type-Options", "nosniff"
        )
        content_security_policy = SecureHeadersMiddleware.Header(
            "Content-Security-Policy", "script-src 'self'; object-src 'self'"
        )
        referrer_policy = SecureHeadersMiddleware.Header(
            "Referrer-Policy", "no-referrer, strict-origin-when-cross-origin"
        )

        self.security_headers = []

        if hsts:
            if type(hsts) == str:
                hsts_header.value = str(hsts)
            self.security_headers.append(hsts_header)

        if xss:
            if type(xss) == str:
                x_xss_protection.value = str(xss)
            self.security_headers.append(x_xss_protection)

        if content_type:
            if type(content_type) == str:
                x_content_type_options.value = str(content_type)
            self.security_headers.append(x_content_type_options)

        if csp:
            if type(csp) == str:
                content_security_policy.value = str(csp)
            self.security_headers.append(content_security_policy)

        if referrer:
            if type(referrer) == str:
                referrer_policy.value = str(referrer)
            self.security_headers.append(referrer_policy)

    def __call__(self, request: Request, app: Any) -> Response:
        response = super().__call__(request, app)

        for item in self.security_headers:
            response.set_header(name=item.header, value=item.value, overwrite=False)

        return response
