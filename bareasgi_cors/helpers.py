"""Helper functions"""

from typing import AbstractSet, Optional

from bareasgi import Application

from .cors_provider import CORSMiddleware


def add_cors_middleware(
        app: Application,
        *,
        allow_origins: Optional[AbstractSet[str]] = None,
        allow_methods: Optional[AbstractSet[str]] = None,
        allow_headers: Optional[AbstractSet[str]] = None,
        allow_credentials: bool = False,
        allow_origin_regex: Optional[str] = None,
        expose_headers: AbstractSet[str] = None,
        max_age: int = 600
) -> Application:
    """Add the CORS middleware.

    Args:
        app (Application): The ASGI application.
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
    cors_middleware = CORSMiddleware(
        allow_origins=allow_origins,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        allow_credentials=allow_credentials,
        allow_origin_regex=allow_origin_regex,
        expose_headers=expose_headers,
        max_age=max_age
    )
    app.middlewares.append(cors_middleware)
    return app
