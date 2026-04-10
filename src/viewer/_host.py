from __future__ import annotations

from dataclasses import dataclass
import json
from queue import Empty, Queue
import sys
import threading
from typing import IO, Callable, cast

import webview


@dataclass
class _HostRequest:
    request_id: int
    title: str
    html: str
    request: object | None


class _ResponseWriter:
    def __init__(self, stream: IO[str]) -> None:
        self._stream: IO[str] = stream
        self._lock: threading.Lock = threading.Lock()

    def send(self, payload: dict[str, object]) -> None:
        message = json.dumps(payload)
        with self._lock:
            _ = self._stream.write(message)
            _ = self._stream.write("\n")
            self._stream.flush()


class _Bridge:
    def __init__(self, response_writer: _ResponseWriter) -> None:
        self._response_writer: _ResponseWriter = response_writer
        self._window: webview.Window | None = None
        self._active_request: _HostRequest | None = None
        self._request_complete: threading.Event = threading.Event()
        self._request_lock: threading.Lock = threading.Lock()

    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    def on_runtime_started(self) -> None:
        if self._window is None:
            raise RuntimeError("Host window is not attached")
        self._window.hide()
        self._response_writer.send({"type": "ready"})

    def present(self, request: _HostRequest) -> None:
        if self._window is None:
            raise RuntimeError("Host window is not attached")

        with self._request_lock:
            self._active_request = request
            self._request_complete.clear()

        self._window.set_title(request.title)
        self._window.load_html(request.html)
        self._window.show()

    def wait_for_completion(self) -> None:
        _ = self._request_complete.wait()

    def get_request(self) -> object | None:
        active_request = self._active_request
        if active_request is None:
            raise RuntimeError("No active viewer request")
        return active_request.request

    def resolve(self, result: object | None = None) -> None:
        self._finish_active_request(ok=True, result=result)

    def cancel(self, reason: str | None = None) -> None:
        self._finish_active_request(
            ok=False,
            error=reason or "Viewer interaction cancelled",
            cancelled=True,
        )

    def on_window_closing(self) -> bool:
        self.cancel()
        return False

    def shutdown(self) -> None:
        if self._window is not None:
            self._window.destroy()

    def _finish_active_request(
        self,
        *,
        ok: bool,
        result: object | None = None,
        error: str | None = None,
        cancelled: bool = False,
    ) -> None:
        if self._window is None:
            raise RuntimeError("Host window is not attached")

        with self._request_lock:
            active_request = self._active_request
            if active_request is None or self._request_complete.is_set():
                self._window.hide()
                return

            response: dict[str, object] = {
                "type": "response",
                "id": active_request.request_id,
                "ok": ok,
            }
            if ok:
                response["result"] = result
            else:
                response["error"] = error or "Viewer request failed"
                response["cancelled"] = cancelled

            self._active_request = None
            self._response_writer.send(response)
            self._request_complete.set()

        self._window.hide()


def run_host(stdin: IO[str], stdout: IO[str]) -> None:
    response_writer = _ResponseWriter(stdout)
    bridge = _Bridge(response_writer)
    request_queue: Queue[_HostRequest | None] = Queue()

    create_window = cast(Callable[..., webview.Window | None], webview.create_window)
    window = create_window(
        title="Viewer",
        html="<html><body></body></html>",
        width=1440,
        height=920,
        min_size=(960, 640),
    )
    if window is None:
        raise RuntimeError("Failed to create viewer window")

    bridge.attach_window(window)
    window.expose(
        bridge.get_request,
        bridge.resolve,
        bridge.cancel,
    )
    window.events.closing += bridge.on_window_closing

    webview.start(
        func=_command_loop,
        args=(bridge, request_queue, stdin, response_writer),
        debug=False,
    )


def _command_loop(
    bridge: _Bridge,
    request_queue: Queue[_HostRequest | None],
    stdin: IO[str],
    response_writer: _ResponseWriter,
) -> None:
    reader = threading.Thread(
        target=_stdin_reader,
        args=(stdin, request_queue, response_writer),
        daemon=True,
    )
    reader.start()
    bridge.on_runtime_started()

    while True:
        try:
            request = request_queue.get(timeout=0.1)
        except Empty:
            continue

        if request is None:
            bridge.shutdown()
            return

        if request.request_id == 0:
            bridge.shutdown()
            return

        bridge.present(request)
        bridge.wait_for_completion()


def _stdin_reader(
    stdin: IO[str],
    request_queue: Queue[_HostRequest | None],
    response_writer: _ResponseWriter,
) -> None:
    for line in stdin:
        text = line.strip()
        if not text:
            continue

        try:
            payload = cast(dict[str, object], json.loads(text))
            request_queue.put(_coerce_request(payload))
        except Exception as exc:
            response_writer.send(
                {
                    "type": "response",
                    "id": -1,
                    "ok": False,
                    "error": str(exc),
                    "cancelled": False,
                }
            )

    request_queue.put(None)


def _coerce_request(raw_request: dict[str, object]) -> _HostRequest:
    request_id = raw_request.get("id")
    command = raw_request.get("command")
    payload = raw_request.get("payload")

    if not isinstance(request_id, int):
        raise TypeError("Viewer request id must be an integer")
    if not isinstance(command, str):
        raise TypeError("Viewer command must be a string")
    if command == "shutdown":
        return _HostRequest(request_id=0, title="Viewer", html="", request=None)
    if command != "show":
        raise TypeError(f"Unknown viewer command: {command}")
    if not isinstance(payload, dict):
        raise TypeError("Viewer payload must be a dictionary")

    typed_payload = cast(dict[str, object], payload)
    title = typed_payload.get("title")
    html = typed_payload.get("html")
    request = typed_payload.get("request")

    if not isinstance(title, str) or not title.strip():
        raise TypeError("Viewer title must be a non-empty string")
    if not isinstance(html, str) or not html.strip():
        raise TypeError("Viewer html must be a non-empty string")

    return _HostRequest(
        request_id=request_id,
        title=title,
        html=html,
        request=request,
    )


def main() -> None:
    run_host(sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
