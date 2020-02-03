# Usage

The support is implemented as middleware.

```python
from bareasgi import Application
from bareasgi_cors import CORSMiddleware

cors_middleware = CORSMiddleware()
app = Application(middlewares=[cors_middleware])
```

# Post Routes

Before issuing a POST across origin an OPTION request will be made. This means that
every post route must also support OPTION.

Here is an example:

```python
app.http_router.add({'POST', 'OPTIONS'}, '/info', set_info)
```
