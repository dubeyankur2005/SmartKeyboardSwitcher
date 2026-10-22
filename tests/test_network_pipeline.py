import queue
import threading

from client.network_server import NetworkServer
from host.network_client import NetworkClient


def test_authenticated_tcp_key_events_receive_injection_acknowledgments():
    token = "test-pairing-token"
    received = []
    received_lock = threading.Lock()
    received_twice = threading.Event()
    host_events = queue.Queue()

    def inject(action, key):
        with received_lock:
            received.append((action, key))
            if len(received) == 2:
                received_twice.set()

    server = NetworkServer(token, lambda *_: None, lambda *_: None, inject)
    client = NetworkClient(lambda *event: host_events.put(event))
    try:
        server.start(0)
        port = server.sock.getsockname()[1]
        client.connect("127.0.0.1", port, token)
        client.send({"type": "key", "action": "down", "key": "A"})
        client.send({"type": "key", "action": "up", "key": "A"})

        assert received_twice.wait(2), "Client did not receive both key transitions"
        successful = []
        while len(successful) < 2:
            event = host_events.get(timeout=2)
            if event[0] == "Injection successful":
                successful.append(event)

        assert received == [("down", "A"), ("up", "A")]
        assert len(successful) == 2
    finally:
        client.disconnect()
        server.stop()


def test_rejected_authentication_closes_host_socket(monkeypatch):
    from host import network_client as module

    class FakeSocket:
        closed = False

        def settimeout(self, timeout):
            pass

        def sendall(self, data):
            pass

        def recv(self, size):
            return b""

        def close(self):
            self.closed = True

    fake_socket = FakeSocket()
    monkeypatch.setattr(module.socket, "create_connection", lambda *args, **kwargs: fake_socket)
    client = NetworkClient(lambda *_: None)

    try:
        try:
            client.connect("127.0.0.1", 8765, "test-pairing-token")
        except ConnectionError as exc:
            assert "closed during authentication" in str(exc)
        else:
            raise AssertionError("Expected authentication to fail")
        assert fake_socket.closed
    finally:
        client.disconnect()


def test_injection_error_is_reported_to_host_and_closes_remote_session():
    token = "test-pairing-token"
    host_events = queue.Queue()

    def fail_injection(action, key):
        raise OSError("SendInput inserted no keyboard events")

    server = NetworkServer(token, lambda *_: None, lambda *_: None, fail_injection)
    client = NetworkClient(lambda *event: host_events.put(event))
    try:
        server.start(0)
        client.connect("127.0.0.1", server.sock.getsockname()[1], token)
        client.send({"type": "key", "action": "down", "key": "A"})

        event = host_events.get(timeout=2)
        while event[0] != "Injection error":
            event = host_events.get(timeout=2)
        assert event == ("Injection error", "SendInput inserted no keyboard events")
    finally:
        client.disconnect()
        server.stop()
