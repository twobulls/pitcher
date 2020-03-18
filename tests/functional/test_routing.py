import pytest

from pitcher import Application, Request, Route
from pitcher.response import Response
from tests.client import HandlerClient


@pytest.mark.parametrize(
    "method,handler",
    [
        ("GET", "read"),
        ("PUT", "update"),
        ("POST", "create"),
        ("DELETE", "delete"),
        ("PATCH", "update"),
    ],
)
def test_method_routing_v1(method, handler):
    def hello_create(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "create"}
        return data

    def hello_read(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "read"}
        return data

    def hello_update(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "update"}
        return data

    def hello_delete(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "delete"}
        return data

    app = Application(
        name="hello",
        base="api",
        routes=[
            Route("/hello", hello_create, methods=["POST"]),
            Route("/hello", hello_read, methods=["GET"]),
            Route("/hello", hello_update, methods=["PUT", "PATCH"]),
            Route("/hello", hello_delete, methods=["DELETE"]),
        ],
    )

    client = HandlerClient(app, version="1.0")

    response = client.request(method, "/api/hello")

    assert response.headers["content-type"] == "application/json"

    json_body = response.json()
    assert json_body["method"] == method
    assert json_body["handler"] == handler


@pytest.mark.parametrize(
    "method,handler",
    [
        ("GET", "read"),
        ("PUT", "update"),
        ("POST", "create"),
        ("DELETE", "delete"),
        ("PATCH", "update"),
    ],
)
def test_method_routing_v2(method, handler):
    def hello_create(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "create"}
        return data

    def hello_read(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "read"}
        return data

    def hello_update(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "update"}
        return data

    def hello_delete(request: Request, app) -> dict:
        data = {"method": request.method, "handler": "delete"}
        return data

    app = Application(
        name="hello",
        routes=[
            Route("/hello", hello_create, methods=["POST"]),
            Route("/hello", hello_read, methods=["GET"]),
            Route("/hello", hello_update, methods=["PUT", "PATCH"]),
            Route("/hello", hello_delete, methods=["DELETE"]),
        ],
    )

    client = HandlerClient(app, version="2.0")

    response = client.request(method, "/hello")

    assert response.headers["content-type"] == "application/json"

    json_body = response.json()
    assert json_body["method"] == method
    assert json_body["handler"] == handler


def test_duplicate_route():
    def hello(request: Request, app) -> Response:
        return Response(204)

    with pytest.raises(ValueError) as excinfo:
        Application(
            name="hello",
            base="api",
            routes=[
                Route("/hello", hello, methods=["POST"]),
                Route("/hello", hello, methods=["GET"]),
                Route("/hello", hello, methods=["PUT", "PATCH"]),
                Route("/hello", hello, methods=["DELETE"]),
                Route("/hello", hello, methods=["GET"]),
            ],
        )

        assert "Duplicate method for path /hello" in str(excinfo.value)


def test_unregistered_route():
    def hello(request: Request, app) -> Response:
        return Response(204)

    app = Application(name="hello", routes=[Route("/hello", hello, methods=["GET"]),],)

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello/{name}", uriparams={"name": "world"})
    assert response.status_code == 404
    assert "Unregistered resource path /hello/{name}" in response.body


def test_unregistered_method():
    def hello(request: Request, app) -> Response:
        return Response(204)

    app = Application(name="hello", routes=[Route("/hello", hello, methods=["POST"]),],)

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello")
    assert response.status_code == 405
    assert "Unregistered view function for path /hello with method GET" in response.body


@pytest.mark.parametrize("input", [("lemon"), ("apple"), ("world"), ("cat"), ("dog")])
def test_path_params(input, lambda_context):
    def hello_world(request: Request, app) -> dict:
        name = request.params["name"]
        data = {"message": f"hello {name}"}
        return data

    app = Application(
        name="hello", routes=[Route("/hello/{name}", hello_world, methods=["ANY"])]
    )

    client = HandlerClient(app)

    response = client.get("/hello/{name}", uriparams={"name": input})

    assert response.headers["content-type"] == "application/json"

    json_body = response.json()

    assert json_body["message"] == f"hello {input}"
