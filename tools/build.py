#!/usr/bin/env python3
"""Build the Luce application natively from its own manifest and sources."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(luce: Path, base: Path, output: Path, opt: int) -> None:
    luce, base, output = (path.resolve() for path in (luce, base, output))
    output.parent.mkdir(parents=True, exist_ok=True)
    # luce stages the emitted Base package in a workspace of its own; the output
    # directory receives only the requested executable.
    environment = dict(os.environ, LUCE_BASE=str(base), LUCE_CACHE=str(ROOT / "build/cache"))
    subprocess.run([str(luce), "build", str(ROOT / "src/main.luc"), "--native", "--opt",
                    str(opt), "-o", str(output)], env=environment, cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--luce", type=Path, default=ROOT.parent / ("luce/build/luce.exe" if os.name == "nt" else "luce/build/luce"))
    parser.add_argument("--base", type=Path, default=Path(os.environ.get(
        "LUCE_BASE_COMPILER", ROOT.parent / ("luce-base/build/luce-base.exe" if os.name == "nt" else "luce-base/build/luce-base"))))
    parser.add_argument("--opt", type=int, choices=range(4), default=0)
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "build/luce-http-server")
    arguments = parser.parse_args()
    build(arguments.luce, arguments.base, arguments.output, arguments.opt)
