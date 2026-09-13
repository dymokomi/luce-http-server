#!/usr/bin/env python3
"""Build the Luce application with a separate Base source package, natively."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build(luce: Path, base: Path, server: Path, output: Path, opt: int) -> None:
    luce, base, server, output = (path.resolve() for path in (luce, base, server, output))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Source staging is private to this invocation and is removed even when a
    # compiler fails. The output directory contains only requested build products.
    with tempfile.TemporaryDirectory(prefix="luce-http-server-") as temporary:
        project = Path(temporary)
        source = project / "src"
        shutil.copytree(ROOT / "src", source)
        (project / "luce.toml").write_text(
            '[package]\nname = "luce_http_server"\nsource = "src"\n\n'
            '[dependencies]\nluce_server = ' + json.dumps(server.as_posix()) + '\n', encoding='utf-8', newline='\n')
        environment = dict(os.environ, LUCE_BASE=str(base))
        subprocess.run([str(luce), "build", str(source / "main.luc"), "--native", "--opt",
                        str(opt), "-o", str(output)], env=environment, cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--luce", type=Path, default=ROOT.parent / ("luce/build/luce.exe" if os.name == "nt" else "luce/build/luce"))
    parser.add_argument("--base", type=Path, default=Path(os.environ.get(
        "LUCE_BASE_COMPILER", ROOT.parent / ("luce-base/build/luce-base.exe" if os.name == "nt" else "luce-base/build/luce-base"))))
    parser.add_argument("--server", type=Path, default=ROOT.parent / "luce-server")
    parser.add_argument("--opt", type=int, choices=range(4), default=0)
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "build/luce-http-server")
    arguments = parser.parse_args()
    build(arguments.luce, arguments.base, arguments.server, arguments.output, arguments.opt)
