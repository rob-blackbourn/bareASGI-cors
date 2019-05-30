import json
import logging
from bareasgi import Application
from baretypes import (
    Scope,
    Info,
    RouteMatches,
    Content,
    HttpResponse
)
from bareutils import (
    text_reader,
    text_writer
)
from bareasgi_cors import CORSMiddleware

logging.basicConfig(level=logging.DEBUG)


async def get_info(scope: Scope, info: Info, matches: RouteMatches, content: Content) -> HttpResponse:
    text = json.dumps(info)
    return 200, [(b'content-type', b'application/json')], text_writer(text)


async def set_info(scope: Scope, info: Info, matches: RouteMatches, content: Content) -> HttpResponse:
    text = await text_reader(content)
    data = json.loads(text)
    info.update(data)
    return 204, None, None


if __name__ == "__main__":
    import uvicorn

    cors_middleware = CORSMiddleware()

    app = Application(info={'name': 'Michael Caine'}, middlewares=[cors_middleware])

    app.http_router.add({'GET'}, '/info', get_info)
    app.http_router.add({'POST', 'OPTIONS'}, '/info', set_info)

    uvicorn.run(app, port=9010)
