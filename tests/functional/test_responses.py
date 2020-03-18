import base64
from datetime import datetime
from decimal import Decimal
import json

import pytest

from pitcher import Application, Request, Route
from pitcher.response import Response, redirect
from pitcher.response import PlainTextResponse, Response
from tests.client import HandlerClient


@pytest.mark.parametrize(
    "path, content_type, expected",
    [
        ("/jpeg", "image/jpeg", "W3JhdyBieXRlc10="),
        ("/json", "application/json", json.dumps({"hello": "world"})),
        ("/text", "text/plain", "hello"),
    ],
)
def test_response_body(path, content_type, expected):
    def hello_jpeg(request: Request, app) -> Response:
        return Response(
            200, base64.b64decode("W3JhdyBieXRlc10="), content_type=content_type
        )

    def hello_json(request: Request, app) -> dict:
        data = {"hello": "world"}
        return data

    def hello_text(request: Request, app) -> Response:
        return PlainTextResponse(200, "hello")

    app = Application(
        name="hello",
        routes=[
            Route("/jpeg", hello_jpeg),
            Route("/json", hello_json),
            Route("/text", hello_text),
        ],
    )

    client = HandlerClient(app, version="2.0")

    response = client.get(path, headers={"Accept": content_type})

    assert response.headers["Content-Type"] == content_type
    assert response.body == expected


def test_json_serializer():
    def hello(request: Request, app) -> dict:
        request_json = request.json_body() if request.json_body() else {}

        now = datetime.utcnow()
        return {
            "now": now,
            "date": now.date(),
            "time": now.time(),
            "decimal": Decimal("1.00000009"),
            "request": {"hello": request_json.get("hello")},
            "size": len(request_json.keys()),
        }

    app = Application(name="hello", routes=[Route("/hello", hello, methods=["ANY"]),],)

    client = HandlerClient(app, version="2.0")

    response = client.post(
        "/hello",
        data=json.dumps({"hello": "world"}),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200

    json_body = response.json()
    assert json_body["decimal"] == "1.00000009"
    assert json_body["request"]["hello"] == "world"


@pytest.mark.parametrize(
    "status,expected_status,expects_location",
    [(301, 301, True), (300, 300, True), (None, 301, True), (200, 500, False)],
)
def test_redirect(status, expected_status, expects_location):
    def hello(request: Request, app) -> Response:
        return redirect("/goodbye", status)

    app = Application(name="hello", routes=[Route("/hello", hello, methods=["POST"]),])

    client = HandlerClient(app, version="2.0")

    response = client.post("/hello")

    assert response.status_code == expected_status
    has_location = True if "location" in response.headers else False
    assert has_location == expects_location


def test_vary():
    def hello(request: Request, app) -> Response:
        name = request.params.get("name", "unknown")
        response = Response(200, {"hello": name})
        response.vary("User-Agent")
        response.vary("Accept-Language")
        return response

    app = Application(name="hello", routes=[Route("/hello/{name}", hello),],)

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello/{name}", uriparams={"name": "world"})
    assert response.status_code == 200
    assert response.headers["Vary"] == "User-Agent, Accept-Language"


def test_vary_star():
    def hello(request: Request, app) -> Response:
        response = Response(204)
        response.vary("*")
        return response

    app = Application(name="hello", routes=[Route("/hello", hello),],)

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello")
    assert response.status_code == 204
    assert response.headers["Vary"] == "*"


@pytest.mark.parametrize(
    "cookies, expected",
    [
        (
            ({"name": "Default", "value": "1"},),
            ["Default=1; Secure; SameSite=Lax; HttpOnly; Path=/"],
        ),
        (
            ({"name": "Encoded", "value": "1 /// [check it out]"},),
            [
                "Encoded=1+%2F%2F%2F+%5Bcheck+it+out%5D; Secure; SameSite=Lax; HttpOnly; Path=/"
            ],
        ),
        (
            ({"name": "Session", "value": "1", "secure": False, "path": None},),
            ["Session=1; SameSite=Lax; HttpOnly"],
        ),
        (
            ({"name": "Session", "value": "1", "same_site": True},),
            ["Session=1; Secure; SameSite=Strict; HttpOnly; Path=/"],
        ),
        (
            ({"name": "Session", "value": "1", "domain": "example.com"},),
            ["Session=1; Secure; SameSite=Lax; HttpOnly; Path=/; Domain=example.com"],
        ),
        (
            ({"name": "__Host-Session", "value": "1", "secure": True},),
            ["__Host-Session=1; Secure; SameSite=Lax; HttpOnly; Path=/"],
        ),
        (
            ({"name": "__Secure-Session", "value": "1", "path": "/api"},),
            ["__Secure-Session=1; Secure; SameSite=Lax; HttpOnly; Path=/api"],
        ),
        (
            ({"name": "__Secure-Session", "value": "1", "http_only": True},),
            ["__Secure-Session=1; Secure; SameSite=Lax; HttpOnly; Path=/"],
        ),
        (
            ({"name": "Expired", "value": "1", "max_age": 0, "http_only": False},),
            ["Expired=1; Secure; SameSite=Lax; Path=/; Max-Age=0"],
        ),
        (
            (
                {
                    "name": "Permanent",
                    "value": "1",
                    "max_age": 2592000,
                    "http_only": False,
                },
            ),
            ["Permanent=1; Secure; SameSite=Lax; Path=/; Max-Age=2592000"],
        ),
        (
            (
                {
                    "name": "Permanent",
                    "value": "1",
                    "expires": datetime.fromisoformat("2021-01-01 16:01"),
                },
            ),
            [
                "Permanent=1; Secure; SameSite=Lax; HttpOnly; Path=/; Expires=2021-01-01T16:01:00"
            ],
        ),
        (
            (
                {
                    "name": "Permanent",
                    "value": "1",
                    "max_age": 2592000,
                    "expires": datetime.fromisoformat("2021-01-01 16:01"),
                },
            ),
            ["Permanent=1; Secure; SameSite=Lax; HttpOnly; Path=/; Max-Age=2592000"],
        ),
    ],
)
def test_cookies(cookies, expected):
    def hello(request: Request, app) -> Response:
        response = Response(204)
        for cookie in cookies:
            response.set_cookie(**cookie)
        return response

    app = Application(name="hello", routes=[Route("/hello", hello),],)

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello")
    print(expected)
    print(response.cookies)
    assert response.status_code == 204
    assert all(elem in response.cookies for elem in expected)


@pytest.mark.parametrize(
    "cookies, error",
    [
        (
            ({"name": "(invalid)", "value": "1", "secure": False},),
            "Invalid name for cookie",
        ),
        (
            ({"name": "__Secure-Number", "value": "1", "secure": False},),
            "must be set as secure",
        ),
        (
            ({"name": "__Host-Number", "value": "1", "secure": False, "path": "/"},),
            "must be set as secure",
        ),
        (
            ({"name": "__Host-Number", "value": "1", "path": "/api"},),
            "Path is required to be set to /",
        ),
        (
            (
                {
                    "name": "__Host-Number",
                    "value": "1",
                    "path": "/",
                    "domain": "example.com",
                },
            ),
            "Domain must not be set",
        ),
    ],
)
def test_cookie_validation(cookies, error):
    def hello(request: Request, app) -> Response:
        response = Response(204)
        for cookie in cookies:
            response.set_cookie(**cookie)
        return response

    app = Application(name="hello", routes=[Route("/hello", hello),],)

    client = HandlerClient(app, version="2.0")

    response = client.get("/hello")

    assert response.status_code == 500
    assert error in response.body
