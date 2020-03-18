import base64
import json
from typing import Any, Dict, Mapping, Optional
from types import MappingProxyType


class CaseInsensitiveDict(dict):
    proxy: Dict[str, Any] = {}

    def __init__(self, data):
        self.proxy = dict((k.lower(), k) for k in data)
        for k in data:
            self[k] = data[k]

    def __contains__(self, k):
        return k.lower() in self.proxy

    def __getitem__(self, k):
        key = self.proxy[k.lower()]
        return super(CaseInsensitiveDict, self).__getitem__(key)

    def get(self, k, default=None):
        return self[k] if k in self else default

    def __setitem__(self, k, v):
        super(CaseInsensitiveDict, self).__setitem__(k, v)
        self.proxy[k.lower()] = k


class Request:
    def __init__(self, event: Mapping[str, Any], context: Any) -> None:
        self.event = event
        self.context = context
        self.version = event.get("version", "1.0")
        self.request_context = event.get("requestContext", {})
        self.id = self.request_context.get("requestId")
        self.headers = MappingProxyType(CaseInsensitiveDict(event.get("headers", {})))
        queryStringParameters = event.get("queryStringParameters", {})
        self.query = MappingProxyType(
            queryStringParameters if queryStringParameters is not None else {}
        )
        stageVariables = event.get("stageVariables", {})
        self.stage_variables = MappingProxyType(
            stageVariables if stageVariables is not None else {}
        )
        self.params = event.get("pathParameters", {}).copy()

        if self.version == "2.0":
            _, resource_path = event.get("routeKey", "").split(" ", 1)
            self.resource_path = resource_path
            self.path = self.request_context.get("http", {}).get("path")
            self.method = self.request_context.get("http", {}).get("method", "GET")
            self.authorizer = event["requestContext"].get("authorizer", {}).get("jwt")
            self.cookies = event.get("cookies", [])
        else:
            self.resource_path = self.request_context.get("resourcePath")
            self.path = self.request_context.get("path")
            self.method = self.request_context.get("httpMethod", "GET")
            self.authorizer = self.request_context.get("authorizer")
            multi_headers = CaseInsensitiveDict(event.get("multiValueHeaders", {}))
            self.cookies = multi_headers.get("cookie", [])

        self.binary = event.get("isBase64Encoded", False)
        if self.binary:
            body = base64.b64decode(event["body"])
        else:
            body = event.get("body", None)

        self.content_type = self.headers.get("content-type", "application/json")
        self.body = body

        self._json_body = None

    def json_body(self) -> Optional[dict]:
        if (
            self.body
            and self.content_type
            and self.content_type.lower().startswith("application/json")
            and self._json_body is None
        ):
            self._json_body = json.loads(self.body)
        return self._json_body
