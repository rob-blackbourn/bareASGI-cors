from typing import List, Mapping, AbstractSet, Optional
import logging
import re
from bareasgi import text_writer
from bareasgi.types import (
    Header,
    Scope,
    Info,
    RouteMatches,
    Content,
    HttpRequestCallback,
    HttpResponse
)
from .headers import find_header_value, headers_to_dict, upsert_header

ALL_METHODS = {"DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"}

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

logger = logging.getLogger(__name__)

class CORSMiddleware:

    def __init__(
        self,
        *,
        allow_origins: Optional[AbstractSet[str]] = None,
        allow_methods: Optional[AbstractSet[str]] = None,
        allow_headers: Optional[AbstractSet[str]] = None,
        allow_credentials: bool = False,
        allow_origin_regex: Optional[str] = None,
        expose_headers: AbstractSet[str] = None,
        max_age: int = 600
    ) -> None:
        """
        Construct the CORS middleware

        :param allow_origins: An optional set of the allowed origins, or None for any origin.
        :param allow_methods: An optional set of allowed methods, or None for all methods.
        :param allow_headers: An optional set of allowed headers, or None for all headers.
        :param allow_credentials: If True allow credentials, otherwise disallow.
        :param allow_origin_regex: An optional regex pattern to apply to origins.
        :param an optional set of headers to expose.
        :param max_age: The maximum age in seconds. Defaults to ten minutes.
        """

        self.allow_methods = allow_methods if allow_methods is not None else ALL_METHODS

        compiled_allow_origin_regex = None
        if allow_origin_regex is not None:
            compiled_allow_origin_regex = re.compile(allow_origin_regex)

        self.simple_headers: List[Header] = []
        self.allow_all_origins = allow_origins is None
        if self.allow_all_origins:
            self.allow_origins = None
            self.simple_headers.append((ACCESS_CONTROL_ALLOW_ORIGIN, b"*"))
        else:
            self.allow_origins = allow_origins

        if allow_credentials:
            self.simple_headers.append((ACCESS_CONTROL_ALLOW_CREDENTIALS, b"true"))

        if expose_headers:
            self.simple_headers.append((ACCESS_CONTROL_EXPOSE_HEADERS, ", ".join(expose_headers).encode()))

        self.preflight_headers: List[Header] = []
        if self.allow_all_origins:
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_ORIGIN, b"*"))
        else:
            self.preflight_headers.append((VARY, b"Origin"))
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_METHODS, ", ".join(self.allow_methods).encode()))
            self.preflight_headers.append((ACCESS_CONTROL_MAX_AGE, str(max_age).encode()))

        self.allow_all_headers = allow_headers is None
        if self.allow_all_headers:
            self.allow_headers = None
        else:
            self.allow_headers = allow_headers
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_HEADERS, ", ".join(allow_headers).encode()))

        if allow_credentials:
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_CREDENTIALS, b"true"))

        self.allow_origin_regex = compiled_allow_origin_regex

    def _preflight_check(self, request_header_map: Mapping[bytes, List[bytes]]) -> HttpResponse:
        try:
            response_headers: List[Header] = list(self.preflight_headers)

            requested_origin = request_header_map[ORIGIN][0]
            if self._is_allowed_origin(origin=requested_origin):
                if not self.allow_all_origins:
                    # If self.allow_all_origins is True, then the "Access-Control-Allow-Origin"
                    # header is already set to "*".
                    # If we only allow specific origins, then we have to mirror back
                    # the Origin header in the response.
                    upsert_header(response_headers, ACCESS_CONTROL_ALLOW_ORIGIN, requested_origin)
            else:
                raise RuntimeError(f'Invalid origin {requested_origin}')

            requested_method = request_header_map[ACCESS_CONTROL_REQUEST_METHOD][0]
            if requested_method.decode() not in self.allow_methods:
                raise RuntimeError(f'Invalid method {requested_method}')

            # If we allow all headers, then we have to mirror back any requested
            # headers in the response.
            if ACCESS_CONTROL_REQUEST_HEADERS in request_header_map:
                access_control_request_header = request_header_map[ACCESS_CONTROL_REQUEST_HEADERS][0]
                if self.allow_all_headers:
                    upsert_header(response_headers, ACCESS_CONTROL_ALLOW_HEADERS, access_control_request_header)
                else:
                    for header in access_control_request_header.decode().split(","):
                        if header.strip() not in self.allow_headers:
                            raise RuntimeError(f'Invalid header {header}')

            logger.debug('Passed preflight checks')

            return 200, response_headers, text_writer("OK")

        except RuntimeError as error:
            logger.warning(f'Failed preflight checks with error {error}')
            # We don't strictly need to use 400 responses here, since its up to
            # the browser to enforce the CORS policy, but its more informative
            # if we do.
            return 400, response_headers, text_writer(str(error))

    def _is_allowed_origin(self, origin: bytes) -> bool:
        if self.allow_all_origins:
            return True

        origin_str = origin.decode()
        if self.allow_origin_regex is not None and self.allow_origin_regex.match(origin_str):
            return True

        return origin_str in self.allow_origins

    async def _simple_response(
            self,
            scope: Scope,
            info: Info,
            matches: RouteMatches,
            content: Content,
            handler: HttpRequestCallback
    ) -> HttpResponse:

        request_headers: List[Header] = scope['headers']

        response_status, response_headers, response_body = await handler(scope, info, matches, content)
        if response_headers is None:
            response_headers = []

        origin = find_header_value(request_headers, ORIGIN)

        # If request includes any cookie headers, then we must respond
        # with the specific origin instead of '*'.
        if self.allow_all_origins and find_header_value(request_headers, COOKIE):
            upsert_header(self.simple_headers, ACCESS_CONTROL_ALLOW_ORIGIN, origin)

        # If we only allow specific origins, then we have to mirror back
        # the Origin header in the response.
        elif not self.allow_all_origins and self._is_allowed_origin(origin=origin):
            upsert_header(response_headers, ACCESS_CONTROL_ALLOW_ORIGIN, origin)
            vary_values = find_header_value(response_headers, VARY)
            if not vary_values:
                response_headers.append((VARY, b'Origin'))
            else:
                upsert_header(response_headers, VARY, vary_values + b',Origin')

        for header in self.simple_headers:
            upsert_header(response_headers, *header)

        return response_status, response_headers, response_body

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
            logger.debug(f'CORS processsing skipped as there is no "{ORIGIN}" header')
            return await handler(scope, info, matches, content)

        if scope["method"] == "OPTIONS" and ACCESS_CONTROL_REQUEST_METHOD in headers:
            logger.debug('Performing preflight checks', extra=scope)
            return self._preflight_check(headers)

        logger.debug('Processing simple response', extra=scope)
        return await self._simple_response(scope, info, matches, content, handler)
