from typing import Callable, List, Optional, Sequence, Any, Mapping
import logging

from .middleware import Middleware
from .router import Router, Route
from .request import Request
from .response import PlainTextResponse, Response
from .exceptions import APIException


class Application:
    def __init__(
        self,
        name: str,
        routes: List[Route],
        base: str = "",
        middleware: Sequence[Middleware] = [],
        logger: Optional[Any] = None,
        on_invocation: List[Callable] = [],
        exception_handler: Optional[Callable[[Exception], Response]] = None,
    ) -> None:
        self.base = base
        self.middleware = middleware
        self.router = Router(base=base, routes=routes)
        self.middleware_stack = self._build_middleware_stack()
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(name)
        self.on_invocation = on_invocation
        self.exception_handler = exception_handler

    def __call__(self, event: Mapping[str, Any], context: Any):
        self.logger.debug("event invocation", extra=event)

        if self.on_invocation:
            for func in self.on_invocation:
                try:
                    func(event, context, self)
                except:
                    self.logger.exception("on_invocation function raised an exception")

        request = Request(event, context)
        self.logger.debug(
            "request: {method} {path}",
            method=request.method,
            path=request.resource_path,
        )

        try:
            response = self.middleware_stack(request, self)
        except APIException as ex:
            response = PlainTextResponse(ex.status_code, ex.message)
        except Exception as ex:
            self.logger.exception("request error")
            if self.exception_handler:
                response = self.exception_handler(ex)
            else:
                response = PlainTextResponse(500, "An internal server error occurred.",)

        self.logger.debug(
            "response status {status_code}", status_code=response.status_code
        )
        return response.render(version=request.version)

    def _build_middleware_stack(self) -> Callable[[Request, Any], Response]:
        # wrap the middleware around the router from last to first

        func = self.router
        for cls, options in reversed(self.middleware):
            func = cls(func, **options)

        return func
