# Validation

The application passes native optimization levels 0–3 on ARM64 macOS and x86-64
Linux. The first complete
[hosted application matrix](https://github.com/dymokomi/luce-http-server/actions/runs/34537494933)
validated REST, static content, file transfers, WebSockets, concurrency and ARC
cleanup through the Base package boundary.

The independent clients check REST status/JSON values, parameter validation,
static asset bytes/MIME types, HEAD behavior, unknown methods/routes, multi-MiB
upload/download equality, atomic overwrite refusal, temporary-file cleanup,
120 concurrent client requests, text/binary WebSockets, ping/pong, close, and
SIGTERM shutdown. The process must exit successfully with empty stderr, including
no ARC leak report.

Full native heap instrumentation subsequently found two compiler/runtime lifetime
issues beyond ARC's object counter: Base's startup argument descriptors and
Luce's worker-local collector/temporary buffers. Both were fixed, covered by
focused compiler regressions, and pinned in `bootstrap/BASE` and `bootstrap/LUCE`.
The final local native matrix passes with those fixes. Running
`python3 tests/integration.py build/luce-http-server-0 --heap` on macOS reports
**zero leaked blocks and zero leaked bytes** for the complete application test.
The [hosted run at `d7842a0`](https://github.com/dymokomi/luce-http-server/actions/runs/34540755343)
also passed both native matrices and the macOS heap check; its artifacts retain
`gate.log` and `heap.log`. Later dependency pins include test-harness corrections
with the same compiler/runtime implementation.

The worker regression in Luce starts 64 tasks with cycles, copied results, and
dynamic failures at every native optimization level. It checks both normal ARC
exit behavior and actual native heap cleanup against the updated Base compiler.
This complements the server's own independent HTTP/WebSocket/TCP/lifetime tests.

The default sibling-checkout build and `./run.sh --port 0` were also exercised
locally after rebuilding both compilers natively. The health endpoint returned
the expected JSON, and SIGTERM produced a successful exit with empty stderr.

This is a development package (`0.1.0-dev`), not a production release declaration.
TLS, databases, and package-manager installation remain separate work.
