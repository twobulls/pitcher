import json
import base64
from typing import Any, Dict, Optional, List
import logging
from datetime import datetime
import re
import urllib.parse
from .serializable import to_serializable
from .exceptions import APIException

logger = logging.getLogger()


class Response:
    def __init__(
        self,
        status_code: int,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        self.data = data
        self._headers = headers if headers else {}
        self.content_type = content_type if content_type else "application/json"
        self._cookies: Dict[str, dict] = {}
        self._vary_headers: List[str] = []

    def vary(self, header: str) -> None:
        if header == "*":
            logger.warning(
                "'Vary: *' is better represented by 'Cache-Control: no-store'"
            )
        self._vary_headers.append(header)

    def set_cookie(
        self,
        name: str,
        value: str,
        path: Optional[str] = "/",
        domain: Optional[str] = None,
        expires: Optional[datetime] = None,
        max_age: Optional[int] = None,
        http_only: bool = True,
        secure: bool = True,
        same_site: bool = False,
    ) -> None:
        if not secure and (name.startswith("__Secure-") or name.startswith("__Host-")):
            raise APIException(f"Cookie with name '{name}' must be set as secure")

        if not re.fullmatch(r"[\w\d_-]+", name, re.A):
            raise APIException(f"Invalid name for cookie {name}")

        if name.startswith("__Host-"):
            if path != "/":
                raise APIException(
                    "Invalid cookie {name}. Path is required to be set to /"
                )
            if domain is not None:
                raise APIException("Invalid cookie {name}. Domain must not be set")

        value = urllib.parse.quote_plus(value)

        flags = []

        if secure:
            flags.append("Secure")

        if same_site:
            flags.append("SameSite=Strict")
        else:
            flags.append("SameSite=Lax")

        if http_only:
            flags.append("HttpOnly")

        if path:
            flags.append(f"Path={path}")

        if domain:
            flags.append(f"Domain={domain}")

        if max_age is not None:
            flags.append(f"Max-Age={max_age}")
        elif expires:
            flags.append(f"Expires={expires.isoformat(timespec='seconds')}")

        self._cookies[name] = {"value": value, "flags": flags}

    def set_header(self, name: str, value: str, overwrite: bool = True) -> None:
        if name in self._headers and not overwrite:
            logger.info("existing header {name} will not be overwritten", name=name)
            return

        self._headers[name] = value

    @property
    def cookies(self) -> List[str]:
        results = []

        for key, record in self._cookies.items():
            value = record["value"]
            flags = "; ".join(record["flags"])

            results.append(f"{key}={value}; {flags}")

        return results

    def render(self, version="1.0") -> Dict[str, Any]:
        headers = self._headers
        response: Dict[str, Any] = {
            "statusCode": self.status_code,
            "isBase64Encoded": False,
        }

        if self._vary_headers:
            headers.update({"Vary": ", ".join(self._vary_headers)})

        cookies = self.cookies
        if cookies:
            if version == "1.0":
                response["multiValueHeaders"]["Set-Cookie"] = cookies
            else:
                response["cookies"] = cookies

        if self.data:
            if self.content_type.lower().startswith("application/json"):
                response["body"] = json.dumps(self.data, default=to_serializable)
            elif isinstance(self.data, bytes):
                data = base64.b64encode(self.data)
                response["body"] = data.decode("ascii")
                response["isBase64Encoded"] = True
            else:
                response["body"] = self.data

            if "content-type" not in headers:
                headers.update({"content-type": self.content_type})

        response["headers"] = headers

        return response


class PlainTextResponse(Response):
    def __init__(
        self,
        status_code: int,
        body: str = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            status_code, data=body, headers=headers, content_type="text/plain"
        )


REDIRECT_CODES = (300, 301, 302, 303, 304, 307, 308)


def redirect(url: str, status_code: Optional[int] = None):
    if status_code is None:
        status_code = 301
    elif status_code not in REDIRECT_CODES:
        raise APIException()
    # TODO: limit to allowed redirect domains
    return Response(status_code, headers={"Location": url})
