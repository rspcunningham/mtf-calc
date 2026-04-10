from __future__ import annotations

import atexit
import json
from queue import Empty
import subprocess
import sys
import threading
from typing import IO, cast


class HtmlViewerError(RuntimeError):
    pass


class HtmlViewerCancelled(HtmlViewerError):
    pass


class HtmlViewer:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._stdin: IO[str] | None = None
        self._stdout: IO[str] | None = None
        self._request_lock: threading.Lock = threading.Lock()
        self._lifecycle_lock: threading.Lock = threading.Lock()
        self._next_request_id: int = 1
        self._closed: bool = False
        _ = atexit.register(self.close)

    def show(
        self,
        html: str,
        *,
        request: object | None = None,
        title: str = "Viewer",
    ) -> object | None:
        if not html.strip():
            raise ValueError("html must be a non-empty string")
        if not title.strip():
            raise ValueError("title must be a non-empty string")

        with self._request_lock:
            self._ensure_started()
            request_id = self._next_request_id
            self._next_request_id += 1

            self._send_message(
                {
                    "id": request_id,
                    "command": "show",
                    "payload": {
                        "title": title,
                        "html": html,
                        "request": request,
                    },
                }
            )

            while True:
                try:
                    message = self._read_message()
                except Empty:
                    self._raise_if_crashed(f"Viewer host died while handling {title!r}")
                    continue

                if message.get("type") != "response":
                    continue
                if message.get("id") != request_id:
                    continue
                if message.get("ok"):
                    return message.get("result")

                error = message.get("error")
                if not isinstance(error, str):
                    error = "Viewer request failed"

                if message.get("cancelled") is True:
                    raise HtmlViewerCancelled(error)
                raise HtmlViewerError(error)

    def close(self) -> None:
        with self._lifecycle_lock:
            self._shutdown(wait_timeout=0.1)

    def _ensure_started(self) -> None:
        with self._lifecycle_lock:
            if self._closed:
                raise HtmlViewerError("Viewer has been closed")
            if self._process is not None:
                return

            process: subprocess.Popen[str] = subprocess.Popen(
                [sys.executable, "-m", "viewer._host"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            if process.stdin is None or process.stdout is None:
                process.kill()
                _ = process.wait(timeout=0.1)
                raise HtmlViewerError("Viewer host pipes are unavailable")

            self._process = process
            self._stdin = process.stdin
            self._stdout = process.stdout
            self._await_ready()

    def _shutdown(self, *, wait_timeout: float) -> None:
        process = self._process
        stdin = self._stdin
        if process is None or stdin is None:
            self._closed = True
            return

        self._closed = True

        try:
            if process.poll() is None:
                self._send_message({"id": 0, "command": "shutdown", "payload": {}})
                _ = process.wait(timeout=wait_timeout)
        except subprocess.TimeoutExpired:
            try:
                process.terminate()
                _ = process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                process.kill()
                _ = process.wait(timeout=0.1)
            except Exception:
                return
        except BaseException:
            try:
                process.terminate()
            except Exception:
                return
        finally:
            self._process = None
            self._stdin = None
            self._stdout = None

    def _await_ready(self) -> None:
        while True:
            try:
                message = self._read_message()
            except Empty:
                self._raise_if_crashed("Viewer host failed to start")
                continue

            if message.get("type") == "ready":
                return

    def _send_message(self, payload: dict[str, object]) -> None:
        if self._stdin is None:
            raise HtmlViewerError("Viewer host stdin is unavailable")
        message = json.dumps(payload)
        _ = self._stdin.write(message)
        _ = self._stdin.write("\n")
        self._stdin.flush()

    def _read_message(self) -> dict[str, object]:
        if self._stdout is None:
            raise HtmlViewerError("Viewer host stdout is unavailable")
        line = self._stdout.readline()
        if line == "":
            raise Empty
        return cast(dict[str, object], json.loads(line))

    def _raise_if_crashed(self, message: str) -> None:
        process = self._process
        if process is None:
            raise HtmlViewerError(message)
        if process.poll() is None:
            return

        exit_code = process.returncode
        self._process = None
        self._stdin = None
        self._stdout = None
        raise HtmlViewerError(f"{message} (exit code {exit_code})")
