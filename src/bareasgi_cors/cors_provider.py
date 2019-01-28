from typing import List, Sequence, Mapping
import re
from bareasgi import (
    Application,
    text_writer
)
from bareasgi.types import (
    Header,
    Scope,
    Info,
    RouteMatches,
    Content,
    HttpRequestCallback,
    HttpResponse
)
from .headers import find_headers, find_header_value, headers_to_dict, upsert_header

ALL_METHODS = ("DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT")

ACCESS_CONTROL_ALLOW_CREDENTIALS = b"access-control-allow-credentials"
ACCESS_CONTROL_ALLOW_HEADERS = b"access-control-allow-headers"
ACCESS_CONTROL_ALLOW_METHODS = b"access-control-allow-methods"
ACCESS_CONTROL_ALLOW_ORIGIN = b"access-control-allow-origin"
ACCESS_CONTROL_EXPOSE_HEADERS = b"access-control-expose-headers"
ACCESS_CONTROL_MAX_AGE = b"access-control-max-age"
ACCESS_CONTROL_REQUEST_METHOD = b"access-control-request-method"
ACCESS_CONTROL_REQUEST_HEADERS = b"access-control-request-headers"
COOKIE = b"cookie"
ORIGIN = b"origin"
VARY = b"vary"

class CORSMiddleware:

    def __init__(
        self,
        app: Application,
        allow_origins: Sequence[str] = (),
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        allow_origin_regex: str = None,
        expose_headers: Sequence[str] = (),
        max_age: int = 600,
    ) -> None:

        if "*" in allow_methods:
            allow_methods = ALL_METHODS

        compiled_allow_origin_regex = None
        if allow_origin_regex is not None:
            compiled_allow_origin_regex = re.compile(allow_origin_regex)

        self.simple_headers: List[Header] = []
        if "*" in allow_origins:
            self.simple_headers.append((ACCESS_CONTROL_ALLOW_ORIGIN, b"*"))
        if allow_credentials:
            self.simple_headers.append((ACCESS_CONTROL_ALLOW_CREDENTIALS, b"true"))
        if expose_headers:
            self.simple_headers.append((ACCESS_CONTROL_EXPOSE_HEADERS, ", ".join(expose_headers).encode()))

        self.preflight_headers: List[Header] = []
        if "*" in allow_origins:
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_ORIGIN, b"*"))
        else:
            self.preflight_headers.append((VARY, b"Origin"))
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_METHODS, ", ".join(allow_methods).encode()))
            self.preflight_headers.append((ACCESS_CONTROL_MAX_AGE, str(max_age).encode()))
        if allow_headers and "*" not in allow_headers:
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_HEADERS, ", ".join(allow_headers).encode()))
        if allow_credentials:
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_CREDENTIALS, b"true"))

        self.app = app
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers
        self.allow_all_origins = "*" in allow_origins
        self.allow_all_headers = "*" in allow_headers
        self.allow_origin_regex = compiled_allow_origin_regex

    async def __call__(
            self,
            scope: Scope,
            info: Info,
            matches: RouteMatches,
            content: Content,
            handler: HttpRequestCallback
    ) -> HttpResponse:
        headers = headers_to_dict(scope['headers'])

        if ORIGIN not in headers:
            return await handler(scope, info, matches, content)

        if scope["method"] == "OPTIONS" and ACCESS_CONTROL_REQUEST_METHOD in headers:
            return await self.preflight_response(headers)
        else:
            return await self.simple_response(scope, info, matches, content, handler)

    async def preflight_response(
            self,
            request_headers: Mapping[bytes, List[bytes]]
    ) -> HttpResponse:
        requested_cookie = COOKIE in request_headers

        headers: List[Header] = list(self.preflight_headers)
        failures = []

        requested_origin = request_headers[ORIGIN][0]
        if self.is_allowed_origin(origin=requested_origin):
            if not self.allow_all_origins:
                # If self.allow_all_origins is True, then the "Access-Control-Allow-Origin"
                # header is already set to "*".
                # If we only allow specific origins, then we have to mirror back
                # the Origin header in the response.
                upsert_header(headers, ACCESS_CONTROL_ALLOW_ORIGIN, requested_origin)
        else:
            failures.append("origin")

        requested_method = request_headers[ACCESS_CONTROL_REQUEST_METHOD][0]
        if requested_method.decode() not in self.allow_methods:
            failures.append("method")

        # If we allow all headers, then we have to mirror back any requested
        # headers in the response.
        if ACCESS_CONTROL_REQUEST_HEADERS in request_headers:
            requested_headers = request_headers[ACCESS_CONTROL_REQUEST_HEADERS][0]
            if self.allow_all_headers:
                upsert_header(headers, ACCESS_CONTROL_ALLOW_HEADERS, requested_headers)
            else:
                for header in requested_headers.decode().split(","):
                    if header.strip() not in self.allow_headers:
                        failures.append("headers")

        # We don't strictly need to use 400 responses here, since its up to
        # the browser to enforce the CORS policy, but its more informative
        # if we do.
        if failures:
            return 400, headers, text_writer("disallowed CORS " + ", ".join(failures))

        return 200, headers, text_writer("OK")

    def is_allowed_origin(self, origin: bytes) -> bool:
        if self.allow_all_origins:
            return True

        origin_str = origin.decode()
        if self.allow_origin_regex is not None and self.allow_origin_regex.match(origin_str):
            return True

        return origin_str in self.allow_origins

    async def simple_response(
            self,
            scope: Scope,
            info: Info,
            matches: RouteMatches,
            content: Content,
            handler: HttpRequestCallback
    ) -> HttpResponse:

        # Clone the headers
        headers = list(scope['headers'])

        origin = find_header_value(headers, ORIGIN)

        # If request includes any cookie headers, then we must respond
        # with the specific origin instead of '*'.
        if self.allow_all_origins and find_header_value(headers, COOKIE):
            upsert_header(self.simple_headers, ACCESS_CONTROL_ALLOW_ORIGIN, origin)

        # If we only allow specific origins, then we have to mirror back
        # the Origin header in the response.
        elif not self.allow_all_origins and self.is_allowed_origin(origin=origin):
            upsert_header(headers, ACCESS_CONTROL_ALLOW_ORIGIN, origin)
            vary_values = find_header_value(headers, VARY)
            if not vary_values:
                headers.append(((VARY, b'Origin')))
            else:
                upsert_header(headers, vary_values + b',Origin')

        for header in self.simple_headers:
            upsert_header(headers, header)

        # Clone the scope and replace the headers.
        scope = dict(scope)
        scope['headers'] = headers

        return await handler(scope, info, matches, content)
