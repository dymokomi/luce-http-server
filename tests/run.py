#!/usr/bin/env python3
"""Build and exercise the Luce example at every native optimization level."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build import build

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=Path, default=Path(os.environ.get('LUCE_BASE_COMPILER', ROOT.parent / 'luce-base/build/luce-base')))
parser.add_argument('--luce', type=Path, default=ROOT.parent / 'luce/build/luce')
parser.add_argument('--server', type=Path, default=ROOT.parent / 'luce-server')
parser.add_argument('--opt', type=int, choices=range(4), action='append')
args = parser.parse_args()
for level in args.opt if args.opt is not None else range(4):
    executable = ROOT / 'build' / f'luce-http-server-{level}'
    build(args.luce, args.base, args.server, executable, level)
    subprocess.run([sys.executable, ROOT / 'tests/integration.py', executable], check=True, timeout=90)
    print(f'PASS native opt {level}', flush=True)
