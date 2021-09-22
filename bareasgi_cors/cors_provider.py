"""CORS Middleware"""

import logging
import re
from typing import List, Mapping, AbstractSet, Optional

from bareasgi import (
    Header,
    HttpRequestCallback,
    HttpRequest,
    HttpResponse,
)
from bareutils import text_writer, header

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
    """A CORS middleware implementation
    """

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
        """Construct the CORS middleware

        Args:
            allow_origins (Optional[AbstractSet[str]], optional): An optional
                set of the allowed origins, or None for any origin.. Defaults
                to None.
            allow_methods (Optional[AbstractSet[str]], optional): An optional
                set of allowed methods, or None for all methods. Defaults to
                None.
            allow_headers (Optional[AbstractSet[str]], optional): An optional
                set of allowed headers, or None for all headers. Defaults to
                None.
            allow_credentials (bool, optional): If True allow credentials,
                otherwise disallow. Defaults to False.
            allow_origin_regex (Optional[str], optional): An optional regex
                pattern to apply to origins. Defaults to None.
            expose_headers (AbstractSet[str], optional): An optional set of
                headers to expose. Defaults to None.
            max_age (int, optional): The maximum age in seconds. Defaults to 600.
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
            self.simple_headers.append(
                (ACCESS_CONTROL_ALLOW_CREDENTIALS, b"true"))

        if expose_headers:
            self.simple_headers.append(
                (ACCESS_CONTROL_EXPOSE_HEADERS, ", ".join(expose_headers).encode()))

        self.preflight_headers: List[Header] = []
        if self.allow_all_origins:
            self.preflight_headers.append((ACCESS_CONTROL_ALLOW_ORIGIN, b"*"))
        else:
            self.preflight_headers.append((VARY, b"Origin"))

        self.preflight_headers.append(
            (ACCESS_CONTROL_ALLOW_METHODS, ", ".join(self.allow_methods).encode()))
        self.preflight_headers.append(
            (ACCESS_CONTROL_MAX_AGE, str(max_age).encode())
        )

        self.allow_all_headers = allow_headers is None
        if allow_headers is None:
            self.allow_headers = None
        else:
            self.allow_headers = allow_headers
            self.preflight_headers.append(
                (ACCESS_CONTROL_ALLOW_HEADERS, ", ".join(allow_headers).encode()))

        if allow_credentials:
            self.preflight_headers.append(
                (ACCESS_CONTROL_ALLOW_CREDENTIALS, b"true"))

        self.allow_origin_regex = compiled_allow_origin_regex

    def _preflight_check(
            self,
            request_header_map: Mapping[bytes, List[bytes]]
    ) -> HttpResponse:
        response_headers: List[Header] = list(self.preflight_headers)

        try:
            requested_origin = request_header_map[ORIGIN][0]
            if self._is_allowed_origin(origin=requested_origin):
                if not self.allow_all_origins:
                    # If self.allow_all_origins is True, then the "Access-Control-Allow-Origin"
                    # header is already set to "*".
                    # If we only allow specific origins, then we have to mirror back
                    # the Origin header in the response.
                    header.upsert(
                        ACCESS_CONTROL_ALLOW_ORIGIN,
                        requested_origin,
                        response_headers
                    )
            else:
                raise RuntimeError(
                    f'Invalid origin {requested_origin!r}'
                )

            requested_method = request_header_map[ACCESS_CONTROL_REQUEST_METHOD][0]
            if requested_method.decode() not in self.allow_methods:
                raise RuntimeError(f'Invalid method {requested_method!r}')

            # If we allow all headers, then we have to mirror back any requested
            # headers in the response.
            if ACCESS_CONTROL_REQUEST_HEADERS in request_header_map:
                access_control_request_header = request_header_map[ACCESS_CONTROL_REQUEST_HEADERS][0]
                if self.allow_all_headers:
                    header.upsert(
                        ACCESS_CONTROL_ALLOW_HEADERS,
                        access_control_request_header,
                        response_headers
                    )
                elif self.allow_headers:
                    for hdr in access_control_request_header.decode().split(","):
                        if hdr.strip() not in self.allow_headers:
                            raise RuntimeError(f'Invalid header {hdr}')

            logger.debug('Passed preflight checks')

            return HttpResponse(200, response_headers, text_writer("OK"))

        except RuntimeError as error:
            logger.warning('Failed preflight checks with error %s', error)
            # We don't strictly need to use 400 responses here, since its up to
            # the browser to enforce the CORS policy, but its more informative
            # if we do.
            return HttpResponse(400, response_headers, text_writer(str(error)))

    def _is_allowed_origin(self, origin: bytes) -> bool:
        if self.allow_all_origins:
            return True

        origin_str = origin.decode()
        if self.allow_origin_regex is not None and self.allow_origin_regex.match(origin_str):
            return True

        if self.allow_origins is None:
            return False

        return origin_str in self.allow_origins

    async def _simple_response(
            self,
            request: HttpRequest,
            handler: HttpRequestCallback
    ) -> HttpResponse:

        request_headers: List[Header] = request.scope['headers']

        response = await handler(request)

        headers = [] if response.headers is None else list(response.headers)

        origin = header.find(ORIGIN, request_headers)
        assert origin is not None

        # If request includes any cookie headers, then we must respond
        # with the specific origin instead of '*'.
        if self.allow_all_origins and header.find(COOKIE, request_headers):
            header.upsert(
                ACCESS_CONTROL_ALLOW_ORIGIN,
                origin,
                self.simple_headers
            )

        # If we only allow specific origins, then we have to mirror back
        # the Origin header in the response.
        elif not self.allow_all_origins and self._is_allowed_origin(origin=origin):
            header.upsert(
                ACCESS_CONTROL_ALLOW_ORIGIN,
                origin,
                headers
            )
            vary_values = header.find(VARY, headers)
            if not vary_values:
                headers.append((VARY, b'Origin'))
            else:
                header.upsert(VARY, vary_values + b',Origin', headers)

        for name, value in self.simple_headers:
            header.upsert(name, value, headers)

        return HttpResponse(
            response.status,
            headers,
            response.body,
            response.pushes
        )

    async def __call__(
            self,
            request: HttpRequest,
            handler: HttpRequestCallback
    ) -> HttpResponse:
        headers = header.to_dict(request.scope['headers'])

        if ORIGIN not in headers:
            logger.debug(
                'CORS processsing skipped as there is no "%s" header',
                ORIGIN
            )
            return await handler(request)

        if (
                request.scope["method"] == "OPTIONS" and
                ACCESS_CONTROL_REQUEST_METHOD in headers
        ):
            logger.debug('Performing preflight checks', extra=request.scope)
            return self._preflight_check(headers)

        logger.debug('Processing simple response', extra=request.scope)
        return await self._simple_response(request, handler)
