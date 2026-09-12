# Validation evidence

2026-09-11 on ARM64 macOS, using the exact Base, Luce and server commits recorded
under `bootstrap/`.

`./test.sh` passes at native optimization levels 0–3. Independent Python clients
verify health/item/greeting REST replies, decoded Unicode in structured JSON,
static content, HEAD, large streamed uploads/downloads, overwrite rejection,
body limits, concurrent clients, malformed requests, WebSocket text/binary/control
frames, SIGTERM, temporary-file cleanup and clean runtime diagnostics.

`python3 tests/integration.py build/luce-http-server-0 --heap` passes with zero
leaked blocks/bytes. The application is entirely Luce; all server/runtime/protocol
implementation is supplied by the separate Base package. Requests are checked
views, while bodies/responses/messages have independent owned lifetimes.

Builds resolve public package exports through a real dependency manifest. Temporary
source workspaces are removed on success and failure. No generated `.lucb` source
or copied dependency tree remains in normal build output.

CI runs the same native matrix on ARM64 macOS and x86-64 Linux. Local evidence does
not claim Linux execution; that workflow result is recorded separately after push.

The checked-propagation update uses Base `cd44f1d`, Luce `2503fb0` and server
`4695d96`. The full native matrix passed after removing redundant Luce `try`
markers; the native heap check again reported zero leaked blocks/bytes.
