"""One-connection TCP tunnel through an HTTP CONNECT proxy.

Used only for Postgres clients in environments where HTTPS is proxied. The
original database hostname remains the TLS hostname; credentials never enter
proxy logs or application logs.
"""
from __future__ import annotations

import os
import select
import socket
import threading
from urllib.parse import urlsplit


class ProxyTunnel:
    def __init__(self, target_host: str, target_port: int, *, proxy_url: str | None = None) -> None:
        proxy_url = proxy_url or os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        if not proxy_url:
            raise RuntimeError("proxy_not_configured")
        parsed = urlsplit(proxy_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.port is None:
            raise RuntimeError("invalid_proxy_config")
        self.target = (target_host, target_port)
        self.proxy = (parsed.hostname, parsed.port)
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self._listener.settimeout(0.2)
        self.port = self._listener.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, name="dietlens-db-tunnel", daemon=True)

    def __enter__(self) -> "ProxyTunnel":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass
        self._thread.join(timeout=1)

    def _serve(self) -> None:
        client = upstream = None
        try:
            while not self._stop.is_set():
                try:
                    client, _ = self._listener.accept()
                    break
                except socket.timeout:
                    continue
                except OSError:
                    return
            if client is None:
                return
            upstream = socket.create_connection(self.proxy, timeout=15)
            connect = f"CONNECT {self.target[0]}:{self.target[1]} HTTP/1.1\r\nHost: {self.target[0]}:{self.target[1]}\r\n\r\n".encode()
            upstream.sendall(connect)
            response = b""
            while b"\r\n\r\n" not in response and len(response) < 8192:
                chunk = upstream.recv(1024)
                if not chunk:
                    break
                response += chunk
            status_line = response.split(b"\r\n", 1)[0]
            if not status_line.startswith(b"HTTP/") or len(status_line.split()) < 2 or status_line.split()[1] != b"200":
                raise OSError("proxy_connect_failed")
            self._relay(client, upstream, self._stop)
        except (OSError, ValueError):
            pass
        finally:
            for connection in (client, upstream):
                if connection is not None:
                    try:
                        connection.close()
                    except OSError:
                        pass

    @staticmethod
    def _relay(left: socket.socket, right: socket.socket, stop: threading.Event) -> None:
        left.settimeout(None); right.settimeout(None)
        while not stop.is_set():
            readable, _, exceptional = select.select([left, right], [], [left, right], 0.5)
            if exceptional:
                return
            for source in readable:
                data = source.recv(65536)
                if not data:
                    return
                (right if source is left else left).sendall(data)
