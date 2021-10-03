# bareASGI-cors

CORS support for [bareASGI](http://github.com/rob-blackbourn/bareasgi) (read the
[docs](https://rob-blackbourn.github.io/bareASGI-cors/))

## Usage

Simply create the `CORSMiddleware` class and put is as the first middleware.

```python
import json
import uvicorn
from bareasgi import (
    Application,
    text_reader,
    text_writer
)
from bareasgi_cors import CORSMiddleware

async def get_info(request):
    text = json.dumps(request.info)
    return HttpResponse(200, [(b'content-type', b'application/json')], text_writer(text))


async def set_info(request):
    text = await text_reader(request.body)
    data = json.loads(text)
    request.info.update(data)
    return HttpResponse(204)

# Create the CORS middleware class
cors_middleware = CORSMiddleware()

# Use the CORS middleware as the first middleware.
app = Application(info={'name': 'Michael Caine'}, middlewares=[cors_middleware])

app.http_router.add({'GET'}, '/info', get_info)
app.http_router.add({'POST', 'OPTIONS'}, '/info', set_info)

uvicorn.run(app, port=9010)
```

## The POST method

In the above example an OPTION method is included with the POST. This
is always required with a POST as a browser will try first with an OPTION.
