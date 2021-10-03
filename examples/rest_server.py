"""Rest server example"""

import json
import logging

from bareasgi import Application, HttpRequest, HttpResponse
from bareutils import (
    text_reader,
    text_writer
)
import uvicorn

from bareasgi_cors import CORSMiddleware

logging.basicConfig(level=logging.DEBUG)


async def get_info(request: HttpRequest) -> HttpResponse:
    """GET request handler"""
    text = json.dumps(request.info)
    return HttpResponse(
        200,
        [(b'content-type', b'application/json')],
        text_writer(text)
    )


async def set_info(request: HttpRequest) -> HttpResponse:
    """POST request handler"""
    text = await text_reader(request.body)
    data = json.loads(text)
    request.info.update(data)
    return HttpResponse(204)


if __name__ == "__main__":

    cors_middleware = CORSMiddleware()

    app = Application(
        info={'name': 'Michael Caine'},
        middlewares=[cors_middleware]
    )

    app.http_router.add({'GET'}, '/info', get_info)
    app.http_router.add({'POST', 'OPTIONS'}, '/info', set_info)

    uvicorn.run(app, port=9010)
