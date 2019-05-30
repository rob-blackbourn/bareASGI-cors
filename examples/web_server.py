import logging
from bareasgi import Application
from baretypes import (
    Scope,
    Info,
    RouteMatches,
    Content,
    HttpResponse
)
from bareutils import text_writer

logging.basicConfig(level=logging.DEBUG)


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
    <form>
        Info: <input name='info' type='text' id='info'><br />
        <button type='button' onclick='postInfo()'>Post</button>
    </form>
    
    <script>
      function postInfo() {
        const element = document.getElementById('info');
        const data = { name: element.value };

        fetch('http://127.0.0.1:9010/info', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        })
          .then(function(response) {
            console.log(response);
            return Promise.resolve('Done');
          });
      }
      
      window.onload = function() {
        fetch('http://127.0.0.1:9010/info')
          .then(function(response) {
            return response.json();
          })
          .then(function(info) {
            const element = document.getElementById('info');
            element.value = info.name;
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
