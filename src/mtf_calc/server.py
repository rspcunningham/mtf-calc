from __future__ import annotations

import argparse
import socket
import threading
import webbrowser

import uvicorn


def _find_open_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the MTF Calculator.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    host = args.host
    port = args.port or _find_open_port(host)
    url = f"http://{host}:{port}/"

    if not args.no_browser:
        threading.Timer(0.35, webbrowser.open, args=(url,)).start()

    print(f"MTF Calculator listening on {url}")

    uvicorn.run(
        "mtf_calc.app:create_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
        reload=True,
    )
