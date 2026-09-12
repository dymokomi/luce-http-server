# luce-http-server

A native HTTP application written entirely in **Luce**, using the separate
[luce-server](https://github.com/dymokomi/luce-server) library written in **Luce
Base**. It demonstrates REST handlers, static pages, uploads/downloads, WebSockets
and multiple application workers.

```sh
./build.sh
./run.sh --port 8080
```

Open <http://127.0.0.1:8080>. The page calls the REST API, uploads a file and exchanges
WebSocket messages. Ctrl-C drains the server and joins its workers. Sibling
checkouts of `luce-base`, `luce`, `luce-server` and this repository are sufficient;
exact tested commits are recorded under `bootstrap/`. Both compilers use native
compilation by default.

## Writing application behavior

A handler takes a scoped request and returns an owned response:

```luce
pub func health(self, request: Request) -> Response!:
    let result = Value()
    result.set_text("status", "ok")
    return Response.json(result)
```

The worker-local factory registers methods directly:

```luce
let api = Api(upload_directory)
let router = Router()
router.get("/api/health", api.health)
router.get("/api/items/{id}", api.item)
router.websocket("/ws/echo", api.websocket_echo)
return router.application()
```

`Value` comes from the standard `json` module. The library supplies `Server`,
`ServerConfig`, `Router`, `Request`, `Response`, `Body`, `StaticRoot` and session
objects. It owns the threads, routing, wire protocols, bounded storage and cleanup.
Adding an endpoint requires only a handler and route declaration. Each worker
constructs its own application state; no worker token or task scheduling appears
in the application.

WebSocket behavior is similarly direct:

```luce
pub func websocket_echo(self, session: Session) -> unit!:
    session.accept()
    while let message = session.receive():
        session.send(message)
```

The example accepts openings without an identity/Origin restriction and chooses
no subprotocol. An application's opening policy belongs in this handler. TLS and
database integration remain future work.

| Endpoint | Behavior |
| --- | --- |
| GET /api/health | JSON health reply |
| GET /api/items/{id} | REST resource; invalid/nonpositive IDs return 400 |
| GET /api/greet?name=Luce | Decoded query value in a structured JSON reply |
| POST /api/echo | Binary echo, limited to 1 MiB; larger input returns 413 |
| PUT /api/files/{name} | Raw file upload; 201 on success, 409 if already present |
| GET /api/files/{name} | File download; missing files return 404 |
| GET /ws/echo | WebSocket text/binary echo |
| GET /... | Static content from the public directory |

GET supports HEAD fallback. API paths support OPTIONS and method-not-allowed
replies and take precedence over the static mount. Uploads are raw request bodies.
The run script creates the default `uploads` directory; custom directory paths
must already exist. Addresses are numeric IPv4/IPv6, and port zero selects a free
port. Startup prints `READY <port>`.

```sh
./build/luce-http-server --address 127.0.0.1 --port 8080 \
  --network-workers 8 --application-workers 3 \
  --public /path/to/public --uploads /path/to/uploads
```

`src/main.luc` configures the server and owns its run operation.
`src/application.luc` declares routes; `src/api.luc` holds application behavior;
`src/settings.luc` parses CLI settings. Static assets live in `public/`.

All application implementation sources are `.luc`. The manifest declares a local
`luce_server` dependency, resolved through the package's actual public exports.
Builds use automatically removed temporary consumer workspaces when overriding
package locations. Normal build output is the binary, with no generated Base code
or staged dependency trees left behind. Tests additionally produce named binaries.

```sh
./test.sh
python3 tests/integration.py build/luce-http-server-0 --heap  # macOS
```

Tests drive real binaries at native optimization levels 0–3 using independent
Python clients. They cover REST validation, Unicode/JSON, static content, large
file transfers, overwrite refusal, HEAD, malformed input, concurrent clients,
WebSocket control/data frames, temporary cleanup and SIGTERM. See
[validation evidence](docs/VALIDATION.md). CI runs the pinned toolchain on ARM64
macOS and x86-64 Linux. Licensed under MIT or Apache-2.0.
