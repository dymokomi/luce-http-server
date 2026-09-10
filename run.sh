#!/bin/sh
# Default local demo layout. Explicit --public/--uploads paths are caller-owned.
set -eu
cd "$(dirname "$0")"
mkdir -p uploads
exec ./build/luce-http-server "$@"
