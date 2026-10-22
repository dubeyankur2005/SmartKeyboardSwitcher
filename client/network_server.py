import logging
import socket
import threading
from shared.protocol import LineBuffer, encode
from shared.security import token_matches

log = logging.getLogger(__name__)


class NetworkServer:
    def __init__(self, token, on_status, on_active, on_key):
        self.token, self.on_status, self.on_active, self.on_key = token, on_status, on_active, on_key
        self.sock = None
        self.client = None
        self.stop_event = threading.Event()
        self.thread = None
        self.lock = threading.Lock()

    def start(self, port):
        self.stop()
        self.stop_event.clear()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", int(port)))
        server.listen(1); server.settimeout(0.5)
        self.sock = server
        self.thread = threading.Thread(target=self._accept, daemon=True)
        self.thread.start()
        self.on_status("Listening", f"Listening on port {port}")

    def _accept(self):
        try:
            while not self.stop_event.is_set():
                try:
                    conn, addr = self.sock.accept()
                except socket.timeout:
                    continue
                conn.settimeout(0.5)
                try:
                    buf = LineBuffer()
                    authenticated = False
                    while not self.stop_event.is_set() and not authenticated:
                        try: data = conn.recv(1024)
                        except socket.timeout: continue
                        if not data: raise ConnectionError("Connection closed")
                        for msg in buf.feed(data):
                            if msg.get("type") != "auth" or not token_matches(self.token, msg.get("token")):
                                raise PermissionError("Authentication failed")
                            conn.sendall(encode({"type":"auth_ok"})); authenticated = True; break
                    if not authenticated:
                        conn.close(); continue
                    with self.lock: self.client = conn
                    self.on_status("Connected", f"Authenticated host at {addr[0]}")
                    self._session(conn, buf)
                except Exception as exc:
                    log.warning("Rejected/ended client connection: %s", exc)
                    try: conn.close()
                    except OSError: pass
                    if not self.stop_event.is_set(): self.on_status("Error", str(exc))
                finally:
                    with self.lock:
                        if self.client is conn: self.client = None
                    self.on_active(False)
        except OSError as exc:
            if not self.stop_event.is_set(): self.on_status("Error", str(exc))
        self.on_active(False)

    def _session(self, conn, buf):
        while not self.stop_event.is_set():
            try: data = conn.recv(1024)
            except socket.timeout: continue
            if not data: break
            for msg in buf.feed(data):
                if msg["type"] == "key":
                    self.on_active(True); self.on_key(msg["action"], msg["key"])
                elif msg["type"] == "ping":
                    conn.sendall(encode({"type":"pong"}))
        try: conn.sendall(encode({"type":"stop"}))
        except OSError: pass
        self.on_status("Listening", "Host disconnected")

    def stop(self):
        self.stop_event.set()
        for sock in (self.sock, self.client):
            if sock:
                try: sock.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                try: sock.close()
                except OSError: pass
        self.sock = self.client = None
        self.on_active(False)
        self.on_status("Stopped", "Server stopped")
