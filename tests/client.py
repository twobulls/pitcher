import base64
import json
import os
from typing import Any, Callable, List, Optional, Union, Dict
import urllib.parse
from uuid import uuid4

from aws_lambda_context import LambdaContext

from pitcher.request import CaseInsensitiveDict

NON_BINARY_MIME_TYPES = ["application/json", "image/svg+xml"]


class Request:
    def __init__(
        self,
        method: str,
        uri: str,
        headers: Optional[dict] = None,
        data: Optional[Union[str, bytes]] = None,
        params: Optional[dict] = None,
        cookies: Optional[List[str]] = None,
        uriparams: Optional[dict] = None,
        stage: Optional[str] = None,
        stage_vars: Optional[dict] = None,
    ) -> None:
        self.method = method.upper()
        self.uri = uri
        self.headers = headers if headers else {}
        self.data = data
        self.cookies = cookies if cookies else []
        self.params = params if params else {}
        self.uriparams = uriparams if uriparams else {}
        self.stage = stage
        self.stage_vars = stage_vars if stage_vars else {}

    def prepare(self, version: str) -> dict:
        req: Dict[str, Any] = {}
        # TODO: update headers
        headers = self.headers.copy()

        path = self.uri.format(**self.uriparams)
        if version == "2.0":
            req = {
                "version": "2.0",
                "routeKey": f"{self.method} {self.uri}",
                "rawPath": path,
                "rawQueryString": urllib.parse.urlencode(self.params),
                "cookies": self.cookies,
                "headers": headers,
                "requestContext": {
                    # "accountId": "111141352137",
                    # "apiId": "0ghrp4qhb8",
                    "domainName": "0ghrp4qhb8.execute-api.ap-southeast-2.amazonaws.com",
                    # "domainPrefix": "0ghrp4qhb8",
                    "http": {
                        "method": self.method,
                        "path": path,
                        "protocol": "HTTP/1.1",
                        "sourceIp": "127.0.0.1",
                        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:74.0) Gecko/20100101 Firefox/74.0",
                    },
                    # "requestId": "KVFi9iMHSwMEKMw=",
                    "routeKey": f"{self.method} {self.uri}",
                    "stage": self.stage,
                    # "time": "01/Apr/2020:22:58:01 +0000",
                    # "timeEpoch": 1585781881243,
                },
                "pathParameters": self.uriparams,
            }

        else:
            req = {
                "path": path,
                "headers": headers,
                "pathParameters": self.uriparams,
                "requestContext": {
                    # "accountId": "123456789",
                    # "resourceId": sha256(self.uri.encode()).hexdigest()[:6],
                    # "stage": "test",
                    "requestId": str(uuid4()),
                    # "identity": {
                    # "cognitoIdentityPoolId": "",
                    # "accountId": "",
                    # "cognitoIdentityId": "",
                    # "caller": "",
                    # "apiKey": "",
                    # "sourceIp": "192.168.100.1",
                    # "cognitoAuthenticationType": "",
                    # "cognitoAuthenticationProvider": "",
                    # "userArn": "",
                    # "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
                    # "user": "",
                    # },
                    "resourcePath": self.uri,
                    "httpMethod": self.method,
                    # "apiId": "wt6mne2s9k",
                },
                "resource": self.uri,
                "httpMethod": self.method,
                "queryStringParameters": self.params,
                "stageVariables": self.stage_vars,
            }

        if self.data is not None:
            req["isBase64Encoded"] = False
            req["headers"]["content-length"] = len(self.data)

            if isinstance(self.data, (bytes, bytearray)):
                req["isBase64Encoded"] = True
                req["body"] = base64.b64encode(self.data)
                if "content-type" not in headers:
                    req["headers"]["content-type"] = "application/octet-stream"

            else:
                req["body"] = self.data

        return req


class Response:
    def __init__(self, request: Request, data: dict) -> None:
        self.request = request
        self.raw_data = data
        self.body = data.get("body", None)
        self.status_code = data.get("statusCode", 200)
        self.headers = CaseInsensitiveDict(data.get("headers", {}))
        self.content_type = self.headers.get("content-type", "application/json")
        self.binary = data.get("isBase64Encoded", False)
        self._multi_headers = CaseInsensitiveDict(
            self.raw_data.get("multiValueHeaders", {})
        )
        self._json_body = None

    @property
    def cookies(self) -> List[str]:
        if "cookies" in self.raw_data:
            return self.raw_data.get("cookies", [])
        else:
            return self._multi_headers.get("set-cookie", [])

    @property
    def text(self) -> Optional[str]:
        if not self.binary:
            return self.body
        return None

    def json(self) -> Optional[dict]:
        if (
            self.body is not None
            and self.content_type
            and self.content_type.lower().startswith("application/json")
            and self._json_body is None
        ):
            self._json_body = json.loads(self.body)
        return self._json_body


class BaseClient:
    def __init__(self, version: str = "1.0") -> None:
        self.version = version

    def get(self, route: str, **kwargs) -> Any:
        return self.request("GET", route, **kwargs)

    def post(self, route: str, **kwargs) -> Any:
        return self.request("POST", route, **kwargs)

    def put(self, route: str, **kwargs) -> Any:
        return self.request("PUT", route, **kwargs)

    def patch(self, route: str, **kwargs) -> Any:
        return self.request("PATCH", route, **kwargs)

    def delete(self, route: str, **kwargs) -> Any:
        return self.request("DELETE", route, **kwargs)

    def options(self, route: str, **kwargs) -> Any:
        return self.request("OPTIONS", route, **kwargs)

    def request(self, method, route, **kwargs):
        raise NotImplementedError()


class HandlerClient(BaseClient):
    def __init__(
        self,
        handler: Callable,
        version: str = "1.0",
        user_agent: str = "Mozilla/5.0",
        host: Optional[str] = None,
    ) -> None:
        super().__init__(version=version)
        self.handler = handler
        self.user_agent = user_agent
        self.host = host
        self.session: Dict[str, Any] = {}

    def request(self, method, route, **kwargs):
        # TODO: use session values
        headers = kwargs.pop("headers", {})

        if "user-agent" not in headers:
            headers["User-Agent"] = self.user_agent

        if self.host and "host" not in headers:
            headers["Host"] = self.host

        request = Request(method, route, headers=headers, **kwargs)
        prepared = request.prepare(self.version)
        response = self.handler(prepared, self.lambda_context)
        return Response(request, response)

    @property
    def lambda_context(self):
        account_id = os.getenv("AWS_ACCOUNT_ID", "123456789")
        region = os.getenv(
            "AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
        )
        function_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME", "test")

        context = LambdaContext()
        context.function_name = function_name
        context.function_version = os.getenv("AWS_LAMBDA_FUNCTION_VERSION")
        context.memory_limit_in_mb = os.getenv("AWS_LAMBDA_FUNCTION_MEMORY_SIZE", 256)
        context.invoked_function_arn = os.getenv(
            "AWS_LAMBDA_FUNCTION_INVOKED_ARN",
            f"arn:aws:lambda:{region}:{account_id}:function:{function_name}",
        )
        context.aws_request_id = str(uuid4())
        return context
