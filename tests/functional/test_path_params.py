import pytest

from pitcher import Application, Request, Route
from pitcher.response import Response
from tests.client import HandlerClient


@pytest.mark.parametrize(
    "route,path,params,type_map",
    [
        (
            "/{proxy+}",
            "/anything/hello-world/9",
            {"proxy+": "anything/hello-world/9"},
            {"proxy+": "str"},
        ),
        ("/hello/{name}", "/hello/world", {"name": "world"}, {"name": "str"}),
        (
            "/books/{title}",
            "/books/how-to-win-friends-and-influence-people-1936",
            {"title": "how-to-win-friends-and-influence-people-1936"},
            {"title": "str"},
        ),
        ("/count/{num}", "/count/9", {"num": "9"}, {"num": "int"}),
        (
            "/users/{id}",
            "/users/57c2e004-0f2b-429d-8b12-2cc6379a3e58",
            {"id": "57c2e004-0f2b-429d-8b12-2cc6379a3e58"},
            {"id": "uuid"},
        ),
        (
            "/accounts/{id}/users/{user_id}",
            "/accounts/57c2e004-0f2b-429d-8b12-2cc6379a3e58/users/1",
            {"id": "57c2e004-0f2b-429d-8b12-2cc6379a3e58", "user_id": "1"},
            {"id": "uuid", "user_id": "int"},
        ),
    ],
)
def test_path_params(route, path, params, type_map):
    def hello(request: Request, app) -> Response:
        return Response(
            200,
            data={
                "path": request.path,
                "param_types": {
                    k: type(v).__name__.lower() for (k, v) in request.params.items()
                },
            },
        )

    app = Application(
        name="hello",
        routes=[
            Route("/hello/{name}", hello),
            Route("/books/{title:slug}", hello),
            Route("/count/{num:int}", hello),
            Route("/users/{id:uuid}", hello),
            Route("/accounts/{id:uuid}/users/{user_id:int}", hello),
            Route("/{proxy+:path}", hello),
        ],
    )

    client = HandlerClient(app, version="2.0")

    response = client.get(route, uriparams=params)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    json_body = response.json()
    assert json_body["path"] == path
    assert json_body["param_types"] == type_map


@pytest.mark.parametrize(
    "route,params",
    [
        ("/count/{num}", {"num": "abc"},),
        ("/users/{id}", {"id": "12345-abcde"},),
        ("/articles/{name}", {"name": "foo/bar-is-great"},),
        ("/articles/{name}", {"name": "foo&bar"},),
        ("/articles/{name}", {"name": "foo.bar"},),
        ("/{proxy+}", {"proxy+": "/anything/foo/bar.html?q=no"},),
    ],
)
def test_invalid_param_values(route, params):
    def hello(request: Request, app) -> Response:
        return Response(204)

    app = Application(
        name="hello",
        routes=[
            Route("/count/{num:int}", hello),
            Route("/users/{id:uuid}", hello),
            Route("/articles/{name:slug}", hello),
            Route("/{proxy+:path}", hello),
        ],
    )

    client = HandlerClient(app, version="2.0")

    response = client.get(route, uriparams=params)

    assert response.status_code == 404


def test_invalid_param_route():
    def hello(request: Request, app) -> Response:
        return Response(204)

    with pytest.raises(ValueError) as excinfo:
        Application(
            name="hello", routes=[Route("/broken/{year:year}", hello),],
        )

        assert "Converter not found for param year" in str(excinfo.value)
