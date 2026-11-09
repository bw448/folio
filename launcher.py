"""Folio desktop launcher: starts the local server and opens the browser."""
from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from server import app

HOST = "127.0.0.1"
PORT = 8788


def port_open() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.3):
            return True
    except OSError:
        return False


def open_browser_when_ready() -> None:
    for _ in range(80):
        if port_open():
            break
        time.sleep(0.25)
    webbrowser.open(f"http://{HOST}:{PORT}")


def main() -> None:
    if port_open():
        webbrowser.open(f"http://{HOST}:{PORT}")
        return
    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="info", access_log=False)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()
