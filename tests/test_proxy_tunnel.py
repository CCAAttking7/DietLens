import socket
import threading
import time
from urllib.parse import urlsplit

import pytest

from dietlens_mvp.proxy_tunnel import ProxyTunnel


class EchoTarget:
    def __init__(self):
        self.listener = socket.socket(); self.listener.bind(("127.0.0.1", 0)); self.listener.listen(5)
        self.port = self.listener.getsockname()[1]; self.stop = threading.Event(); self.thread = threading.Thread(target=self.run, daemon=True); self.thread.start()
    def run(self):
        self.listener.settimeout(.2)
        while not self.stop.is_set():
            try: client, _ = self.listener.accept()
            except socket.timeout: continue
            except OSError: return
            threading.Thread(target=self.echo, args=(client,), daemon=True).start()
    @staticmethod
    def echo(client):
        with client:
            data=client.recv(65536); client.sendall(data)
    def close(self):
        self.stop.set(); self.listener.close(); self.thread.join(1)


class ConnectProxy:
    def __init__(self, target_host, target_port):
        self.target=(target_host,target_port); self.listener=socket.socket(); self.listener.bind(("127.0.0.1",0)); self.listener.listen(5); self.port=self.listener.getsockname()[1]; self.requests=[]; self.stop=threading.Event(); self.thread=threading.Thread(target=self.run,daemon=True); self.thread.start()
    def run(self):
        self.listener.settimeout(.2)
        while not self.stop.is_set():
            try: client,_=self.listener.accept()
            except socket.timeout: continue
            except OSError:return
            threading.Thread(target=self.handle,args=(client,),daemon=True).start()
    def handle(self, client):
        with client:
            request=b""
            while b"\r\n\r\n" not in request and len(request)<4096: request += client.recv(1024)
            self.requests.append(request)
            upstream=socket.create_connection(self.target, timeout=3)
            with upstream:
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                data=client.recv(65536); upstream.sendall(data); client.sendall(upstream.recv(65536))
    def close(self):
        self.stop.set(); self.listener.close(); self.thread.join(1)


def test_connect_tunnel_relays_and_closes_promptly():
    target=EchoTarget(); proxy=ConnectProxy("127.0.0.1", target.port)
    try:
        tunnel=ProxyTunnel("example.internal", target.port, proxy_url=f"http://127.0.0.1:{proxy.port}")
        with tunnel:
            client=socket.create_connection(("127.0.0.1",tunnel.port),timeout=3); client.sendall(b"hello"); assert client.recv(5)==b"hello"; client.close()
        assert proxy.requests and b"CONNECT example.internal:" in proxy.requests[0]
    finally: proxy.close(); target.close()


def test_tunnel_repeated_instances_do_not_reuse_dead_listener():
    target=EchoTarget(); proxy=ConnectProxy("127.0.0.1", target.port)
    try:
        for _ in range(3):
            with ProxyTunnel("example.internal", target.port, proxy_url=f"http://127.0.0.1:{proxy.port}") as tunnel:
                client=socket.create_connection(("127.0.0.1",tunnel.port),timeout=3); client.sendall(b"x"); assert client.recv(1)==b"x"; client.close()
        assert len(proxy.requests)==3
    finally: proxy.close(); target.close()


def test_non_200_connect_is_not_forwarded():
    listener=socket.socket(); listener.bind(("127.0.0.1",0)); listener.listen(1); port=listener.getsockname()[1]
    def reject():
        client,_=listener.accept()
        with client:
            client.recv(4096); client.sendall(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
    thread=threading.Thread(target=reject,daemon=True);thread.start()
    try:
        with ProxyTunnel("example.internal",5432,proxy_url=f"http://127.0.0.1:{port}") as tunnel:
            client=socket.create_connection(("127.0.0.1",tunnel.port),timeout=3); client.sendall(b"x")
            try:
                assert client.recv(1)==b""
            except ConnectionResetError:
                pass
            finally:
                client.close()
    finally: listener.close();thread.join(1)
