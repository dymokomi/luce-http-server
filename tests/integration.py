#!/usr/bin/env python3
"""Exercise the actual Luce application through independent network clients."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
import os
from pathlib import Path
import select
import queue
import threading
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def finish_process(process, timeout):
    """Wait for the owned process, not pipe EOF from macOS diagnostic helpers."""
    streams = (process.stdout, process.stderr)
    chunks = ([], [])
    for stream in streams:
        os.set_blocking(stream.fileno(), False)
    deadline = time.monotonic() + timeout
    while True:
        for stream, output in zip(streams, chunks):
            data = stream.read1(65536)
            if data:
                output.append(data)
        if process.poll() is not None:
            for stream, output in zip(streams, chunks):
                while data := stream.read1(65536):
                    output.append(data)
            return tuple(b''.join(output) for output in chunks)
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args, timeout,
                output=b''.join(chunks[0]), stderr=b''.join(chunks[1]))
        time.sleep(.01)


def startup_line(process):
    if os.name != 'nt':
        ready, _, _ = select.select([process.stdout], [], [], 15)
        assert ready, 'application startup timed out'
        return process.stdout.readline()
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    try:
        return lines.get(timeout=15)
    except queue.Empty:
        raise AssertionError('application startup timed out') from None


def request_shutdown(process_id):
    if os.name != 'nt':
        os.kill(process_id, signal.SIGTERM)
        return
    # The server owns a hidden console. A short-lived helper attaches to that
    # console to deliver a real CTRL_BREAK event without signaling the test host.
    helper = r"""
import ctypes, sys, time
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
handler_type = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint32)
handler = handler_type(lambda event: 1)
kernel.FreeConsole()
assert kernel.AttachConsole(int(sys.argv[1])), ctypes.get_last_error()
assert kernel.SetConsoleCtrlHandler(handler, True), ctypes.get_last_error()
assert kernel.GenerateConsoleCtrlEvent(1, 0), ctypes.get_last_error()
time.sleep(.1)
kernel.FreeConsole()
"""
    subprocess.run([sys.executable, '-c', helper, str(process_id)], check=True, timeout=5)


def frame(opcode, payload=b''):
    mask = os.urandom(4)
    length = len(payload)
    header = bytes((0x80 | opcode, 0x80 | length)) if length < 126 else bytes((0x80 | opcode, 0x80 | 126)) + struct.pack('!H', length)
    return header + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(payload))


def read_frame(stream):
    header = stream.read(2)
    assert len(header) == 2, header
    opcode, size = header
    assert opcode & 0x80 and not size & 0x80, header
    if size == 126:
        size = struct.unpack('!H', stream.read(2))[0]
    data = stream.read(size)
    assert len(data) == size
    return opcode & 15, data


def check(binary, heap=False):
    with tempfile.TemporaryDirectory(prefix='luce-http-app-') as temporary:
        root = Path(temporary)
        public, uploads = root / 'public', root / 'uploads'
        shutil.copytree(ROOT / 'public', public)
        uploads.mkdir()
        command = [str(binary), '--port', '0', '--public', str(public),
            '--uploads', str(uploads), '--network-workers', '8', '--application-workers', '3']
        if heap:
            if sys.platform != 'darwin':
                raise RuntimeError('--heap requires the macOS leaks tool')
            command = ['/usr/bin/leaks', '--quiet', '--noContent', '--atExit', '--', *command]
        launch = {}
        if os.name == 'nt':
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            launch = dict(creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startup)
        process = subprocess.Popen(command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **launch)
        application_pid = process.pid
        try:
            line = startup_line(process)
            if not line.startswith(b'READY '):
                stdout, stderr = process.communicate(timeout=5)
                raise AssertionError((line, process.returncode, stdout, stderr))
            port = int(line.split()[1])
            if heap:
                # leaks is a parent wrapper and does not forward SIGTERM. Only
                # target its own application child; never search by program name.
                children = subprocess.check_output(['pgrep', '-P', str(process.pid)], text=True).split()
                assert len(children) == 1, children
                application_pid = int(children[0])

            def request(method, path, data=None, headers=None):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=8)
                try:
                    connection.request(method, path, body=data, headers=headers or {})
                    response = connection.getresponse()
                    return response.status, dict(response.getheaders()), response.read()
                finally:
                    connection.close()

            status, headers, page = request('GET', '/')
            assert status == 200 and page == (public / 'index.html').read_bytes()
            assert headers['Content-Type'].startswith('text/html')
            assert request('HEAD', '/')[2] == b''
            assert request('GET', '/style.css')[2] == (public / 'style.css').read_bytes()
            status, _, body = request('GET', '/api/health')
            assert status == 200 and json.loads(body) == {'status': 'ok'}
            assert json.loads(request('GET', '/api/items/42')[2])['id'] == 42
            for value in ('0', '-1', 'x', '999999999999999999999999999'):
                assert request('GET', '/api/items/' + value)[0] == 400
            name = 'Luce "friends" €'
            assert json.loads(request('GET', '/api/greet?name=' + quote(name))[2]) == {'message': f'Hello, {name}!'}
            for value in ('%ff', '%00', '%x', '%22%0d'):
                assert request('GET', '/api/greet?name=' + value)[0] == 400
            assert request('DELETE', '/api/health')[0] == 405
            assert request('OPTIONS', '/api/health')[0] == 204
            assert request('GET', '/does-not-exist')[0] == 404
            assert request('GET', '/api/files/missing')[0] == 404
            assert request('GET', '/api/files/%2e%2e')[0] == 400
            data = bytes(range(256)) * 15000
            status, _, body = request('PUT', '/api/files/payload.bin', data)
            assert status == 201 and json.loads(body)['stored'] is True
            assert (uploads / 'payload.bin').read_bytes() == data
            assert request('PUT', '/api/files/payload.bin', b'unchanged')[0] == 409
            assert (uploads / 'payload.bin').read_bytes() == data
            assert request('GET', '/api/files/payload.bin')[2] == data
            status, headers, body = request('HEAD', '/api/files/payload.bin')
            assert status == 200 and int(headers['Content-Length']) == len(data) and not body
            assert request('POST', '/api/echo', data[:100000])[2] == data[:100000]
            assert request('POST', '/api/echo', data)[0] == 413
            with ThreadPoolExecutor(max_workers=16) as clients:
                def check_client(index):
                    value = f'client-{index}'
                    status, _, body = request('GET', '/api/greet?name=' + value)
                    assert status == 200 and json.loads(body)['message'] == f'Hello, {value}!'
                list(clients.map(check_client, range(120)))
            with socket.create_connection(('127.0.0.1', port), timeout=5) as peer:
                with peer.makefile('rb') as stream:
                    key = base64.b64encode(os.urandom(16))
                    peer.sendall(b'GET /ws/echo HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: ' + key + b'\r\n\r\n')
                    assert stream.readline().startswith(b'HTTP/1.1 101')
                    fields = {}
                    while True:
                        line = stream.readline()
                        assert line
                        if line == b'\r\n': break
                        key_name, value = line.split(b':', 1)
                        fields[key_name.lower()] = value.strip()
                    expected = base64.b64encode(hashlib.sha1(key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
                    assert fields[b'sec-websocket-accept'] == expected
                    for opcode, payload in [(1, 'Hello €'.encode()), (2, bytes(range(256)) * 100), (9, b'ping')]:
                        peer.sendall(frame(opcode, payload))
                        assert read_frame(stream) == (10 if opcode == 9 else opcode, payload)
                    peer.sendall(frame(8, b'\x03\xe8'))
                    assert read_frame(stream) == (8, b'\x03\xe8')
            # A body spilled to disk is released after both the network and Luce
            # ARC owners finish. Wait for this asynchronous ownership handoff.
            deadline = time.monotonic() + 3
            while set(p.name for p in uploads.iterdir()) != {'payload.bin'} and time.monotonic() < deadline:
                time.sleep(.01)
            assert set(p.name for p in uploads.iterdir()) == {'payload.bin'}
            request_shutdown(application_pid)
            stdout, stderr = finish_process(process, 30) if heap else process.communicate(timeout=10)
            if heap:
                assert stdout.startswith(b'STOPPED\n') and b'0 leaks for 0 total leaked bytes' in stdout, stdout
                print(stdout.decode(), end='')
            else:
                assert stdout == b'STOPPED\n', stdout
            assert process.returncode == 0 and stderr == b'', (process.returncode, stdout, stderr)
        finally:
            if process.poll() is None:
                if application_pid != process.pid:
                    try:
                        os.kill(application_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.kill()
                process.communicate()
        print('PASS Luce application: REST, static, streamed files, concurrent clients, WebSocket, ARC cleanup, graceful shutdown', flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--heap', action='store_true', help='also check native heap cleanup on macOS')
    arguments = parser.parse_args()
    check(arguments.binary.resolve(), arguments.heap)
