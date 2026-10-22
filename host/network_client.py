import logging
import socket
import threading
from shared.protocol import LineBuffer, encode

log = logging.getLogger(__name__)


class NetworkClient:
    def __init__(self, on_event):
        self.on_event = on_event
        self.sock = None
        self.lock = threading.Lock()
        self.reader = None
        self.stop_event = threading.Event()

    def connect(self, address, port, token):
        self.disconnect()
        self.stop_event.clear()
        sock = socket.create_connection((address, int(port)), timeout=5)
        sock.settimeout(0.5)
        sock.sendall(encode({"type": "auth", "token": token}))
        buf = LineBuffer()
        deadline = __import__("time").monotonic() + 5
        while __import__("time").monotonic() < deadline:
            try:
                chunk = sock.recv(1024)
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError("Client closed during authentication")
            msgs = buf.feed(chunk)
            if msgs:
                if msgs[0] != {"type": "auth_ok"}:
                    raise ConnectionError("Client rejected authentication")
                break
        else:
            raise TimeoutError("Authentication timed out")
        with self.lock:
            self.sock = sock
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()
        self.on_event("Connected", "Authenticated with Laptop B")

    def send(self, event):
        with self.lock:
            sock = self.sock
            if sock is None:
                raise ConnectionError("Not connected")
            sock.sendall(encode(event))

    def _read_loop(self):
        buf = LineBuffer()
        try:
            while not self.stop_event.is_set():
                try:
                    chunk = self.sock.recv(1024)
                except socket.timeout:
                    continue
                if not chunk:
                    raise ConnectionError("Laptop B disconnected")
                for msg in buf.feed(chunk):
                    if msg.get("type") == "stop":
                        self.on_event("Disconnected", "Client stopped the session")
                        return
        except Exception as exc:
            if not self.stop_event.is_set():
                log.warning("Network reader stopped: %s", exc)
                self.on_event("Disconnected", str(exc))
        finally:
            self._close_socket()

    def _close_socket(self):
        with self.lock:
            sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def disconnect(self):
        self.stop_event.set()
        self._close_socket()
