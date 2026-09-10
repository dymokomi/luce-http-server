# luce-http-server

A native HTTP application written entirely in **Luce**, using the separate
[`luce-server`](https://github.com/dymokomi/luce-server) library written in
**luce-base**. It demonstrates REST handlers, static pages, file uploads/downloads,
WebSockets, and multiple application workers with deterministic resource cleanup.

## Run locally

Use sibling checkouts of `luce-base`, `luce`, `luce-server`, and this repository.
The exact compatible commits are recorded in `bootstrap/BASE`, `bootstrap/LUCE`,
and `bootstrap/SERVER`. Both compilers use Base's native backend.

```sh
# After building the pinned Base and Luce compilers:
./build.sh
./run.sh --port 8080
```

Open <http://127.0.0.1:8080>. The demo calls a REST endpoint, uploads a file, and
exchanges WebSocket messages. Ctrl-C drains the server and joins its workers.

The run script creates the default `uploads` directory. To invoke the binary
directly, create your directories first:

```sh
./build/luce-http-server --address 127.0.0.1 --port 8080 \
  --network-workers 8 --application-workers 3 \
  --public /path/to/public --uploads /path/to/uploads
```

The address must be numeric IPv4 or IPv6. Port zero selects a free port; startup
prints `READY <port>`. Custom directory paths must already exist. Files uploaded
through the demo go to the configured upload directory and never replace an
existing file.

## Write an API

A handler is an ordinary Luce function:

```luce
import luce_server.http as http
from settings import Settings

pub func health(request: http.Request, config: Settings) -> unit!:
    try http.json(request, 200, "{\"status\":\"ok\"}")
```

Add the function to the catalog in `src/application.luc`:

```luce
Route(method = "GET", pattern = "/api/health", handler = api.health)
```

Base matches the method/path and queues an owned request. A Luce worker invokes
the handler, and Base sends its reply. The `with` scope releases each request;
ARC owns values returned across the boundary. The application passes only plain
configuration and an opaque integer worker token across Luce task boundaries.
Handles stay on the worker that owns them.

Routing supports decoded `{name}` path parameters, query values, explicit status
codes and custom response headers. `http.json` sets the media type; handlers
supply serialized JSON. The sample item handler validates its integer ID, then
returns an illustrative resource. There is no database yet.

| Endpoint | Behavior |
| --- | --- |
| GET /api/health | JSON health reply |
| GET /api/items/{id} | Example REST resource; invalid IDs return 400 |
| GET /api/greet?name=Luce | Decoded query value in a JSON reply |
| POST /api/echo | Binary echo, limited to 1 MiB; larger input returns 413 |
| PUT /api/files/{name} | Raw file upload; 201 on success, 409 if already present |
| GET /api/files/{name} | File download; missing files return 404 |
| GET /ws/echo | WebSocket text/binary echo |
| GET /... | Static content from the public directory |

GET routes support HEAD fallback; registered API paths support automatic OPTIONS
and return 405 for unsupported methods. API routes take precedence over the
static mount. Uploads are raw request bodies, not multipart forms. The browser
uses PUT with the selected File as its body.

The WebSocket echo endpoint accepts offered connections without identity/Origin
restrictions and chooses no subprotocol. It is a local demonstration endpoint;
a real application's policy belongs in its opening handler. TLS and database
integration are separate future work.

## Source layout

- `src/main.luc` configures and owns the server lifetime.
- `src/settings.luc` parses plain configuration values.
- `src/application.luc` registers routes and runs Luce application workers.
- `src/api.luc` implements application behavior.
- `public/` contains the browser demo.
- `tests/` drives the real native executable with independent Python clients.

All application implementation sources are `.luc`. The build script stages the
unchanged Base package into an isolated consumer source tree because the package
manager is not implemented yet. It does not substitute a C server implementation.
The compiler consumes that tree through normal Luce/Base interop and produces a
native executable.

## Reproduce the toolchain and tests

From a directory containing all four repositories, use dedicated clean checkouts
at the pins (avoid switching a checkout with local work). In the Base checkout,
run `./build.sh`. In the Luce checkout, run:

```sh
LUCE_BASE_COMPILER=../luce-base/build/luce-base ./build.sh
```

Then, in this checkout:

```sh
./test.sh
```

Custom compiler/package locations are supported:

```sh
./test.sh --base /path/to/luce-base --luce /path/to/luce \
  --server /path/to/luce-server
```

Tests cover all native optimization levels 0–3: REST validation, static assets,
large file transfers, overwrite refusal, HEAD, malformed input, concurrent
clients, WebSocket text/binary/control frames, temporary cleanup and SIGTERM.
A clean exit with empty stderr also checks Luce's ARC leak diagnostics. CI builds
the pinned toolchain from source on ARM64 macOS and x86-64 Linux.
See [validation evidence](docs/VALIDATION.md).

Licensed under MIT or Apache-2.0, at your option.
