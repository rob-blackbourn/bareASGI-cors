from bareasgi import (
    Application,
    Scope,
    Info,
    RouteMatches,
    Content,
    HttpResponse,
    text_writer
)


async def http_request_callback(scope: Scope, info: Info, matches: RouteMatches, content: Content) -> HttpResponse:
    page = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Server</title>
  </head>
  <body>
    Info: <span id='info'></span>
    
    <script>
      window.onload = function() {
        fetch('http://127.0.0.1:9010/info')
          .then(function(response) {
            return response.json();
          })
          .then(function(info) {
            span = document.getElementById('info');
            span.textContent = info.name;
          });
      }
    </script>
  </body>
</html>    
    """
    return 200, [(b'content-type', b'text/html')], text_writer(page)


if __name__ == "__main__":
    import uvicorn

    app = Application()
    app.http_router.add({'GET'}, '/{path}', http_request_callback)

    uvicorn.run(app, port=9009)
