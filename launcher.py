"""Folio desktop launcher: a native window around the local FastAPI app.

The UI is still the same local web app, but it is rendered in a WebView2
window without browser chrome, address bar or tabs. No external browser is
opened. If WebView2 is unavailable, fall back to the default browser.
"""
from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

import uvicorn

from server import app

HOST = "127.0.0.1"
PORT = 8788
URL = f"http://{HOST}:{PORT}"
WINDOW_URL = f"{URL}/?v=0.9.3"
TITLE = "Folio"

FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
ICON = RESOURCE_DIR / "folio.ico"
LOCAL_DIR = Path(os.environ.get("LOCALAPPDATA", str(APP_DIR))) / "Folio"
LOG_PATH = LOCAL_DIR / "desktop.log"


def _force_light_titlebar() -> None:
    """Keep the native title bar light even when Windows is in dark mode."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi
        pid = os.getpid()

        def candidates() -> list[tuple[int, int]]:
            found: list[tuple[int, int]] = []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def callback(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                if buffer.value != TITLE:
                    return True
                proc = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc))
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
                found.append((int(hwnd), area if proc.value == pid else area // 2))
                return True

            user32.EnumWindows(callback, 0)
            return found

        for _ in range(80):
            windows = sorted(candidates(), key=lambda item: item[1], reverse=True)
            if windows:
                hwnd = windows[0][0]
                for _ in range(4):
                    off = ctypes.c_int(0)
                    for attr in (20, 19):
                        dwmapi.DwmSetWindowAttribute(
                            ctypes.c_void_p(hwnd), attr,
                            ctypes.byref(off), ctypes.sizeof(off),
                        )
                    caption = ctypes.c_int(0x00F5F5F7)
                    dwmapi.DwmSetWindowAttribute(
                        ctypes.c_void_p(hwnd), 35,
                        ctypes.byref(caption), ctypes.sizeof(caption),
                    )
                    border = ctypes.c_int(0x00E5E5EA)
                    dwmapi.DwmSetWindowAttribute(
                        ctypes.c_void_p(hwnd), 34,
                        ctypes.byref(border), ctypes.sizeof(border),
                    )
                    text = ctypes.c_int(0x001D1D1F)
                    dwmapi.DwmSetWindowAttribute(
                        ctypes.c_void_p(hwnd), 36,
                        ctypes.byref(text), ctypes.sizeof(text),
                    )
                    time.sleep(0.2)
                return
            time.sleep(0.1)
    except Exception:  # noqa: BLE001
        pass


def _setup_logging() -> None:
    try:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        log = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
        sys.stdout = log
        sys.stderr = log
    except OSError:
        pass


def _message(text: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, text, TITLE, 0x10)
    except Exception:  # noqa: BLE001
        print(text)


def _alive() -> bool:
    try:
        with urlopen(f"{URL}/api/home", timeout=0.6) as response:
            return response.status == 200 and b"documents" in response.read(400)
    except Exception:  # noqa: BLE001
        return False


def _port_open() -> bool:
    import socket

    try:
        with socket.create_connection((HOST, PORT), timeout=0.3):
            return True
    except OSError:
        return False


def _start_server() -> uvicorn.Server:
    config = uvicorn.Config(
        app, host=HOST, port=PORT, log_level="warning", access_log=False,
    )
    server = uvicorn.Server(config)
    # Signal handlers only work on the main thread.
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
    threading.Thread(target=server.run, name="folio-server", daemon=True).start()
    for _ in range(80):
        if _alive():
            break
        time.sleep(0.25)
    return server


def main() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Folio.Reader")
        except Exception:  # noqa: BLE001
            pass

    server = None
    if not _alive():
        if _port_open():
            _message(f"端口 {PORT} 已被其他程序占用。请关闭占用该端口的程序后再启动 Folio。")
            return
        server = _start_server()
        if not _alive():
            _message("Folio 本地服务启动失败。详见 %LOCALAPPDATA%\\Folio\\desktop.log")
            return

    try:
        import webview

        screen = webview.screens[0]
        width = max(960, min(1440, screen.width - 80))
        height = max(640, min(900, screen.height - 80))
        x = max(0, (screen.width - width) // 2)
        y = max(0, (screen.height - height) // 2)
        webview.create_window(
            TITLE,
            WINDOW_URL,
            width=width,
            height=height,
            x=x,
            y=y,
            min_size=(960, 640),
            background_color="#f5f5f7",
            text_select=True,
            zoomable=True,
            confirm_close=False,
        )
        storage_path = LOCAL_DIR / "webview"
        storage_path.mkdir(parents=True, exist_ok=True)
        threading.Thread(target=_force_light_titlebar, daemon=True).start()
        webview.start(
            debug=False,
            private_mode=False,
            storage_path=str(storage_path),
            icon=str(ICON) if ICON.exists() else None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"WebView2 window failed: {exc}")
        webbrowser.open(WINDOW_URL)
        # Keep the server alive while the browser is open.
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        if server is not None:
            server.should_exit = True


if __name__ == "__main__":
    _setup_logging()
    main()
