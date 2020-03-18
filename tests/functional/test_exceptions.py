import importlib

import pytest

from pitcher import Application, Request, Route
from pitcher.exceptions import APIException
from pitcher.response import PlainTextResponse, Response
from tests.client import HandlerClient


@pytest.mark.parametrize(
    "exception, status",
    [
        ("APIException", 500),
        ("BadRequest", 400),
        ("NotFound", 404),
        ("MethodNotAllowed", 405),
    ],
)
def test_api_errors(exception, status):
    def hello(request: Request, app) -> dict:
        module = importlib.import_module("pitcher.exceptions")
        ex_class = getattr(module, exception)
        raise ex_class()

    app = Application(name="hello", routes=[Route("/hello", hello)],)

    client = HandlerClient(app)

    response = client.get("/hello")

    assert response.status_code == status


@pytest.mark.parametrize(
    "message, status",
    [
        ("Not Acceptable", 406),
        ("I'm a teapot", 418),
        ("Too Many Requests", 429),
        ("oh no", None),
    ],
)
def test_custom_error(message, status):
    def hello(request: Request, app) -> dict:
        raise APIException(message, status)

    app = Application(name="hello", routes=[Route("/hello", hello)],)

    client = HandlerClient(app)
    response = client.get("/hello")

    assert response.status_code == status if status else 500
    assert response.body == message


def test_internal_error():
    def hello(request: Request, app) -> Response:
        raise Exception()

    app = Application(name="hello", routes=[Route("/hello", hello),],)

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello")
    assert response.status_code == 500


def test_custom_error_handler():
    def hello(request: Request, app) -> Response:
        raise Exception()

    def custom_exception_handler(ex: Exception) -> Response:
        return PlainTextResponse(418, "I'm a teapot")

    app = Application(
        name="hello",
        routes=[Route("/hello", hello),],
        exception_handler=custom_exception_handler,
    )

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello")
    assert response.status_code == 418
