# bareasgi-cors

CORS support for [bareASGI](http://github.com/rob-blackbourn/bareasgi) (read the [documentation](https://bareasgi-cors.readthedocs.io/en/latest/))

## Usage

A convenience function is provided.

```python
import json
import logging
import uvicorn
from bareasgi import (
    Application,
    text_reader,
    text_writer
)
from bareasgi_cors import CORSMiddleware

logging.basicConfig(level=logging.DEBUG)

async def get_info(scope, info, matches, content):
    text = json.dumps(info)
    return 200, [(b'content-type', b'application/json')], text_writer(text)


async def set_info(scope, info, matches, content):
    text = await text_reader(content)
    data = json.loads(text)
    info.update(data)
    return 204, None, None

cors_middleware = CORSMiddleware()

app = Application(info={'name': 'Michael Caine'}, middlewares=[cors_middleware])

app.http_router.add({'GET'}, '/info', get_info)
app.http_router.add({'POST', 'OPTIONS'}, '/info', set_info)

uvicorn.run(app, port=9010)
```

## The POST method

In the above example an OPTION method is included with the POST. This
is always required with a POST as a browser will try first with an OPTION.
