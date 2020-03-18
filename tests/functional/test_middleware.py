import pytest

from pitcher import Application, Request, Route
from pitcher.middleware import (
    AllowedHostMiddleware,
    CORSMiddleware,
    Middleware,
    SecureHeadersMiddleware,
)
from tests.client import HandlerClient


@pytest.mark.parametrize(
    "hosts,status",
    [
        (["api.example.com"], 200),
        (["*.example.com"], 200),
        (["*.example.com", "*.example.org"], 200),
        (["*"], 200),
        (["*.example.org"], 400),
        (["example.com"], 400),
        (["bar.example.com", "foo.example.org"], 400),
    ],
)
def test_allowed_hosts(hosts, status):
    def hello_world(request: Request, app) -> dict:
        return {"message": "world"}

    app = Application(
        name="hello",
        routes=[Route("/hello", hello_world)],
        middleware=[Middleware(AllowedHostMiddleware, allowed_hosts=hosts),],
    )

    client = HandlerClient(app)

    response = client.get(
        "/hello", headers={"Host": "api.example.com", "Origin": "example.com",},
    )

    assert response.status_code == status


@pytest.mark.parametrize(
    "origin, cors_options, headers",
    [
        (
            "example.com",
            {
                "allow_origins": ["example.com"],
                "allow_methods": ["GET", "POST", "PUT"],
                "allow_credentials": True,
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET, POST, PUT",
                "Access-Control-Allow-Credentials": "true",
                "content-type": "application/json",
                "Vary": "Origin",
            },
        ),
        (
            "example.com",
            {
                "allow_origins": ["api.example.com", "example.org", "example.com",],
                "allow_headers": ["authorization", "content-type"],
                "allow_methods": ["GET"],
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET",
                "content-type": "application/json",
                "Vary": "Origin",
            },
        ),
        (
            "example.com",
            {
                "allow_origins": ["api.example.com", "example.org", "example.com",],
                "allow_headers": ["authorization", "content-type"],
                "allow_methods": ["*"],
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "DELETE, GET, OPTIONS, PATCH, POST, PUT",
                "content-type": "application/json",
                "Vary": "Origin",
            },
        ),
        (
            "example.com",
            {"allow_origins": ["*"], "allow_headers": ["*"]},
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "content-type": "application/json",
            },
        ),
        (
            "example.com",
            {"allow_origins": ["example.net"], "allow_headers": ["*"]},
            {
                "Access-Control-Allow-Methods": "GET",
                "content-type": "application/json",
            },
        ),
        (
            None,
            {"allow_origins": ["example.net"], "allow_headers": ["*"]},
            {"content-type": "application/json",},
        ),
    ],
)
def test_simple_cors(origin, cors_options, headers):
    def hello_world(request: Request, app) -> dict:
        return {"message": "world"}

    app = Application(
        name="hello",
        routes=[Route("/hello", hello_world)],
        middleware=[Middleware(CORSMiddleware, **cors_options),],
    )

    client = HandlerClient(app)

    response = client.get(
        "/hello", headers={"Host": "api.example.com", "Origin": origin,},
    )

    assert response.status_code == 200
    assert response.headers == headers


@pytest.mark.parametrize(
    "origin, request_method, status, cors_options, headers",
    [
        (
            "example.com",
            "GET",
            200,
            {
                "allow_origins": ["example.com"],
                "allow_methods": ["GET", "POST", "PUT"],
                "allow_credentials": True,
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET, POST, PUT",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "600",
                "content-type": "text/plain",
                "Vary": "Origin",
            },
        ),
        (
            "example.com",
            "DELETE",
            400,
            {
                "allow_origins": ["*"],
                "allow_methods": ["GET", "POST", "PUT"],
                "allow_credentials": True,
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET, POST, PUT",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "600",
                "content-type": "text/plain",
            },
        ),
        (
            "example.com",
            "GET",
            200,
            {
                "allow_origins": ["api.example.com", "example.org", "example.com",],
                "allow_headers": ["authorization", "content-type"],
                "allow_methods": ["GET"],
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "authorization, content-type",
                "Access-Control-Max-Age": "600",
                "content-type": "text/plain",
                "Vary": "Origin",
            },
        ),
        (
            "example.com",
            "GET",
            200,
            {"allow_origins": ["*"], "allow_headers": ["*"]},
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Max-Age": "600",
                "content-type": "text/plain",
            },
        ),
        (
            "example.com",
            "POST",
            400,
            {"allow_origins": ["*"], "allow_headers": ["*"]},
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Max-Age": "600",
                "content-type": "text/plain",
            },
        ),
        (
            "example.net",
            "GET",
            400,
            {"allow_origins": ["example.com"], "allow_headers": ["*"]},
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Max-Age": "600",
                "Vary": "Origin",
                "content-type": "text/plain",
            },
        ),
    ],
)
def test_cors_preflight(
    origin, request_method, status, cors_options, headers, lambda_context
):
    def hello_world(request: Request, app) -> dict:
        return {"message": "world"}

    app = Application(
        name="hello",
        routes=[Route("/hello", hello_world, methods=["ANY"])],
        middleware=[Middleware(CORSMiddleware, **cors_options),],
    )

    client = HandlerClient(app)

    response = client.options(
        "/hello",
        headers={
            "Access-Control-Request-Method": request_method,
            "Host": "api.example.com",
            "Origin": origin,
        },
    )

    assert response.status_code == status
    assert response.headers == headers


@pytest.mark.parametrize(
    "hosts,status,cors_options,headers",
    [
        (
            ["api.example.com"],
            200,
            {
                "allow_origins": ["example.com"],
                "allow_methods": ["GET", "POST", "PUT"],
                "allow_credentials": True,
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET, POST, PUT",
                "Access-Control-Allow-Credentials": "true",
                "content-type": "application/json",
                "Vary": "Origin",
            },
        ),
        (
            ["*.example.com"],
            200,
            {
                "allow_origins": ["api.example.com", "example.org", "example.com",],
                "allow_headers": ["authorization", "content-type"],
                "allow_methods": ["GET"],
            },
            {
                "Access-Control-Allow-Origin": "example.com",
                "Access-Control-Allow-Methods": "GET",
                "content-type": "application/json",
                "Vary": "Origin",
            },
        ),
        (
            ["*"],
            200,
            {"allow_origins": ["*"], "allow_headers": ["*"]},
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "content-type": "application/json",
            },
        ),
        (
            ["*.example.org"],
            400,
            {"allow_origins": ["*"], "allow_headers": ["*"]},
            {"content-type": "text/plain"},
        ),
    ],
)
def test_combination(hosts, status, cors_options, headers):
    def hello_world(request: Request, app) -> dict:
        return {"message": "world"}

    app = Application(
        name="hello",
        routes=[Route("/hello", hello_world)],
        middleware=[
            Middleware(AllowedHostMiddleware, allowed_hosts=hosts),
            Middleware(CORSMiddleware, **cors_options),
        ],
    )

    client = HandlerClient(app)

    response = client.get(
        "/hello", headers={"Host": "api.example.com", "Origin": "example.com",},
    )

    assert response.status_code == status
    assert response.headers == headers


@pytest.mark.parametrize(
    "options, headers",
    [
        (
            {},
            {
                "Strict-Transport-Security": "max-age=2592000; includeSubdomains",
                "X-XSS-Protection": "1; mode=block",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer, strict-origin-when-cross-origin",
                "content-type": "application/json",
            },
        ),
        (
            {"referrer": False, "content_type": False,},
            {
                "Strict-Transport-Security": "max-age=2592000; includeSubdomains",
                "X-XSS-Protection": "1; mode=block",
                "content-type": "application/json",
            },
        ),
        (
            {"hsts": "max-age=31536000; includeSubdomains", "csp": True, "xss": False},
            {
                "Strict-Transport-Security": "max-age=31536000; includeSubdomains",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer, strict-origin-when-cross-origin",
                "Content-Security-Policy": "script-src 'self'; object-src 'self'",
                "content-type": "application/json",
            },
        ),
        (
            {
                "hsts": False,
                "xss": "0",
                "content_type": "nosniff",
                "csp": "default-src 'self'",
                "referrer": "no-referrer",
            },
            {
                "X-XSS-Protection": "0",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'",
                "content-type": "application/json",
            },
        ),
    ],
)
def test_secure_headers(options, headers):
    def hello_world(request: Request, app) -> dict:
        return {"message": "world"}

    app = Application(
        name="hello",
        routes=[Route("/hello", hello_world)],
        middleware=[Middleware(SecureHeadersMiddleware, **options),],
    )

    client = HandlerClient(app)

    response = client.get("/hello",)

    assert response.status_code == 200
    assert response.headers == headers
