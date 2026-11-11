"""Folio desktop launcher: a native window around the local FastAPI app.

The UI is still the same local web app, but it is rendered in a WebView2
window without browser chrome, address bar or tabs. No external browser is
opened. If WebView2 is unavailable, fall back to the default browser.
"""
from __future__ import annotations

import ctypes
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

import uvicorn

from server import app

HOST = "127.0.0.1"
PREFERRED_PORT = 8788
TITLE = "Folio"
APP_VERSION = "0.9.1"
MUTEX_NAME = "Local\\Folio.SingleInstance"

FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
ICON = RESOURCE_DIR / "folio.ico"
LOCAL_DIR = Path(os.environ.get("LOCALAPPDATA", str(APP_DIR))) / "Folio"
LOG_PATH = LOCAL_DIR / "desktop.log"
INSTANCE_PATH = LOCAL_DIR / "instance.json"


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


def _alive(port: int) -> bool:
    try:
        with urlopen(f"http://{HOST}:{port}/api/home", timeout=0.8) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read(8000).decode("utf-8", "replace"))
            return isinstance(payload, dict) and "documents" in payload
    except Exception:  # noqa: BLE001
        return False


def _bind(port: int) -> socket.socket | None:
    """Bind a TCP socket without SO_REUSEADDR (Windows would hijack the port)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((HOST, port))
    except OSError:
        sock.close()
        return None
    return sock


def _start_server() -> tuple[uvicorn.Server | None, int]:
    """Start on 8788 when free, otherwise on an OS-assigned free port."""
    sock = _bind(PREFERRED_PORT)
    if sock is None:
        sock = _bind(0)
    if sock is None:
        return None, PREFERRED_PORT
    port = int(sock.getsockname()[1])
    config = uvicorn.Config(
        app, host=HOST, port=port, log_level="warning", access_log=False,
    )
    server = uvicorn.Server(config)
    # Signal handlers only work on the main thread.
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
    threading.Thread(
        target=server.run,
        kwargs={"sockets": [sock]},
        name="folio-server",
        daemon=True,
    ).start()
    for _ in range(80):
        if _alive(port):
            return server, port
        time.sleep(0.25)
    server.should_exit = True
    return None, port


def _acquire_mutex() -> tuple[bool, int | None]:
    """Return (acquired, handle). acquired=False means Folio already runs here."""
    if sys.platform != "win32":
        return True, None
    try:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not handle:
            return True, None
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return False, None
        return True, int(handle)
    except Exception:  # noqa: BLE001
        return True, None


def _focus_existing() -> bool:
    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found: list[int] = []

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
            found.append(int(hwnd))
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return False

        user32.EnumWindows(callback, 0)
        return bool(found)
    except Exception:  # noqa: BLE001
        return False


def _read_instance() -> dict | None:
    try:
        payload = json.loads(INSTANCE_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError):
        return None


def _write_instance(port: int) -> None:
    try:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        INSTANCE_PATH.write_text(
            json.dumps({"pid": os.getpid(), "port": port, "url": f"http://{HOST}:{port}"}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _clear_instance() -> None:
    try:
        info = _read_instance() or {}
        if int(info.get("pid") or 0) == os.getpid():
            INSTANCE_PATH.unlink()
    except Exception:  # noqa: BLE001
        pass


def _hand_off_to_running() -> None:
    """Bring the running window forward, or open its URL as a fallback."""
    for _ in range(20):
        if _focus_existing():
            return
        time.sleep(0.25)
    info = _read_instance() or {}
    port = info.get("port")
    if isinstance(port, int) and _alive(port):
        webbrowser.open(f"http://{HOST}:{port}/?v={APP_VERSION}")
        return
    _message("Folio 已在运行，请在任务栏中切换到它的窗口。")


def main() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Folio.Reader")
        except Exception:  # noqa: BLE001
            pass

    acquired, mutex = _acquire_mutex()
    if not acquired:
        _hand_off_to_running()
        return

    server = None
    try:
        server, port = _start_server()
        if server is None or not _alive(port):
            _message("Folio 本地服务启动失败。详见 %LOCALAPPDATA%\\Folio\\desktop.log")
            return
        _write_instance(port)
        window_url = f"http://{HOST}:{port}/?v={APP_VERSION}"

        try:
            import webview

            screen = webview.screens[0]
            width = max(960, min(1440, screen.width - 80))
            height = max(640, min(900, screen.height - 80))
            x = max(0, (screen.width - width) // 2)
            y = max(0, (screen.height - height) // 2)
            webview.create_window(
                TITLE,
                window_url,
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
            webbrowser.open(window_url)
            # Keep the server alive while the browser is open.
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    finally:
        if server is not None:
            server.should_exit = True
        _clear_instance()
        if mutex:
            try:
                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(mutex))
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    _setup_logging()
    main()
