from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

from .converters import get_converter
from .exceptions import APIException, MethodNotAllowed, NotFound
from .request import Request
from .response import PlainTextResponse, Response

ACCEPTED_METHODS = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "ANY"]


@dataclass(frozen=True)
class RouteEntry:
    view_func: Callable
    converters: Optional[Dict[str, Callable[[str], Any]]] = None


class Route:
    def __init__(
        self,
        path: str,
        view_func: Callable[[Request, Any], Any],
        methods: List[str] = ["GET"],
    ) -> None:
        self.path = path
        self.view_func = view_func
        self.methods = methods


class Router:
    def __init__(self, base: str, routes: Sequence[Route]) -> None:
        self.base = base.strip("/")
        self.routes: Dict[str, Dict[str, RouteEntry]] = defaultdict(dict)
        path_segment_regex = r"\{(?P<param>\w+\+?)\:(?P<type>\w+)\}"
        self.path_segment_regex = re.compile(path_segment_regex)
        for route in routes:
            self._register_route(route)

    def _register_route(self, route: Route) -> None:
        methods = [
            method.upper()
            for method in route.methods
            if method.upper() in ACCEPTED_METHODS
        ]

        converters = {}

        path = route.path.strip("/")

        if "{" in path:
            segments = []
            for segment in path.split("/"):
                match = self.path_segment_regex.fullmatch(segment)
                if match:
                    param_name, type_name = match.group(1, 2)
                    converter = get_converter(type_name)
                    if converter is None:
                        raise ValueError(
                            f"Converter not found for param {param_name} in path {route.path}"
                        )
                    converters[param_name] = converter
                    segments.append(f"{{{param_name}}}")
                else:
                    segments.append(segment)

            path = "/".join(segments)

        path = "/" + path

        if self.base:
            path = f"/{self.base}{path}"

        for method in methods:
            if method in self.routes[path]:
                raise ValueError(f"Duplicate method for path {route.path}")
            else:
                self.routes[path][method] = RouteEntry(route.view_func, converters)

    def __call__(self, request: Request, app: Any) -> Response:
        key = request.resource_path
        if key is None:
            raise APIException(message="invalid resource path")

        try:
            resource_routes = self.routes.get(key)
            if resource_routes is None:
                raise NotFound(f"Unregistered resource path {key}")

            entry = resource_routes.get(request.method)
            if entry is None:
                entry = resource_routes.get("ANY")

            if entry is None or not callable(entry.view_func):
                raise MethodNotAllowed(
                    f"Unregistered view function for path {key} with method {request.method}"
                )

            if entry.converters:
                for param_name, converter in entry.converters.items():
                    try:
                        value = request.params[param_name]
                        request.params[param_name] = converter(value)
                    except:
                        app.logger.info(
                            "{param_name} failed to convert {value} using {converter}",
                            param_name=param_name,
                            value=request.params[param_name],
                            converter=converter,
                        )
                        raise NotFound(f"{param_name} param failed to match type")

            response = entry.view_func(request, app)
            if not isinstance(response, Response):
                response = Response(200, data=response)
        except APIException as ex:
            response = PlainTextResponse(ex.status_code, ex.message)

        return response
