import json
import base64

import pytest

from pitcher import Application, Request, Route
from pitcher import Response
from tests.client import HandlerClient


@pytest.mark.parametrize(
    "content_type,body",
    [
        ("application/json", json.dumps({"hello": "2001-01-01"})),
        ("text/plain", "hello"),
        ("image/jpeg", base64.b64decode("W3JhdyBieXRlc10=")),
    ],
)
def test_request_body(content_type, body):
    def hello(request: Request, app) -> Response:
        return Response(200, {"result": request.body == body})

    app = Application(name="hello", routes=[Route("/hello", hello, methods=["ANY"]),],)

    client = HandlerClient(app, version="2.0")

    response = client.post("/hello", data=body, headers={"Content-Type": content_type})

    assert response.status_code == 200

    json_body = response.json()
    assert json_body["result"]
