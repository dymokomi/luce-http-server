# Validation

The application passes local ARM64 macOS native builds and integration checks at
optimization levels 0–3. The pinned toolchain builds Luce with Base natively and
builds this application through Luce's normal Base boundary.

The independent clients check REST status/JSON values, parameter validation,
static asset bytes/MIME types, HEAD behavior, unknown methods/routes, multi-MiB
upload/download equality, atomic overwrite refusal, temporary-file cleanup,
120 concurrent client requests, text/binary WebSockets, ping/pong, close, and
SIGTERM shutdown. The process must exit successfully with empty stderr, including
no ARC leak report.

Hosted ARM64 macOS and x86-64 Linux validation is recorded here after completion.
This is a development package (`0.1.0-dev`), not a production release declaration.
