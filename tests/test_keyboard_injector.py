import ctypes

import pytest

from client import keyboard_injector as injector_module
from client.keyboard_injector import INPUT, KEYBDINPUT, KeyboardInjector, VK


def test_input_structure_matches_windows_abi():
    # MOUSEINPUT is the largest INPUT union member, including pointer padding.
    assert ctypes.sizeof(INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    assert ctypes.sizeof(KEYBDINPUT) == (24 if ctypes.sizeof(ctypes.c_void_p) == 8 else 16)


@pytest.mark.parametrize("key,vk", [("A", 0x41), ("F2", 0x71), ("LEFT", 0x25), ("RCTRL", 0xA3)])
def test_supported_keys_convert_to_virtual_keys(key, vk):
    assert VK[key] == vk


def test_sendinput_receives_complete_structure_and_keyup_flag(monkeypatch):
    calls = []

    class FakeSendInput:
        def __call__(self, count, item_ptr, size):
            item = ctypes.cast(item_ptr, ctypes.POINTER(INPUT)).contents
            calls.append((count, size, item.type, item.ki.wVk, item.ki.dwFlags))
            return 1

    class FakeUser32:
        SendInput = FakeSendInput()

    monkeypatch.setattr(injector_module.ctypes, "WinDLL", lambda *args, **kwargs: FakeUser32())
    KeyboardInjector._send(VK["A"], True)
    assert calls == [(1, ctypes.sizeof(INPUT), 1, VK["A"], 0x0002)]


def test_key_down_and_up_update_held_state(monkeypatch):
    calls = []
    monkeypatch.setattr(injector_module.os, "name", "nt")
    injector = KeyboardInjector()
    monkeypatch.setattr(injector, "_send", lambda vk, keyup: calls.append((vk, keyup)))

    injector.event("down", "A")
    assert injector.held == {"A"}
    injector.event("up", "A")
    assert injector.held == set()
    assert calls == [(0x41, False), (0x41, True)]


@pytest.mark.parametrize("action,key", [("repeat", "A"), ("down", "NOT_A_KEY"), (None, "A"), ("up", None)])
def test_invalid_keyboard_events_are_rejected(action, key):
    with pytest.raises(ValueError):
        KeyboardInjector().event(action, key)


def test_failed_key_down_is_not_marked_held(monkeypatch):
    monkeypatch.setattr(injector_module.os, "name", "nt")
    injector = KeyboardInjector()

    def fail_send(vk, keyup):
        raise OSError("SendInput failed")

    monkeypatch.setattr(injector, "_send", fail_send)
    with pytest.raises(OSError, match="SendInput failed"):
        injector.event("down", "A")
    assert injector.held == set()


def test_release_all_sends_keyups_even_if_one_fails(monkeypatch):
    monkeypatch.setattr(injector_module.os, "name", "nt")
    injector = KeyboardInjector()
    injector.held = {"A", "SHIFT"}
    calls = []

    def send(vk, keyup):
        calls.append((vk, keyup))
        if vk == VK["A"]:
            raise OSError("failed release")

    monkeypatch.setattr(injector, "_send", send)
    with pytest.raises(OSError, match="Could not release all"):
        injector.release_all()
    assert set(calls) == {(VK["A"], True), (VK["SHIFT"], True)}
    assert injector.held == set()


def test_injection_error_does_not_mark_remote_input_active():
    from client.network_server import NetworkServer
    from shared.protocol import LineBuffer, encode, decode_line

    class FakeSocket:
        def __init__(self):
            self.sent = False
            self.outgoing = []

        def recv(self, size):
            if self.sent:
                return b""
            self.sent = True
            return encode({"type": "key", "action": "down", "key": "A"})

        def sendall(self, data):
            self.outgoing.append(data)

    active = []
    conn = FakeSocket()
    def fail_injection(action, key):
        raise OSError("SendInput inserted no keyboard events")

    server = NetworkServer("a-long-secret", lambda *_: None, active.append, fail_injection)
    with pytest.raises(OSError, match="SendInput inserted no"):
        server._session(conn, LineBuffer())
    assert active == []
    assert decode_line(conn.outgoing[0].strip()) == {
        "type": "injection_error", "detail": "SendInput inserted no keyboard events"
    }


def test_received_down_and_up_events_are_injected_then_acknowledged():
    from client.network_server import NetworkServer
    from shared.protocol import LineBuffer, encode, decode_line

    class FakeSocket:
        def __init__(self):
            self.received = False
            self.sent = []

        def recv(self, size):
            if self.received:
                return b""
            self.received = True
            return (encode({"type": "key", "action": "down", "key": "A"})
                    + encode({"type": "key", "action": "up", "key": "A"}))

        def sendall(self, data):
            self.sent.append(data)

    injected, statuses, active = [], [], []
    conn = FakeSocket()
    server = NetworkServer(
        "a-long-secret",
        lambda status, detail: statuses.append((status, detail)),
        active.append,
        lambda action, key: injected.append((action, key)),
    )
    server._session(conn, LineBuffer())

    assert injected == [("down", "A"), ("up", "A")]
    assert [decode_line(frame.strip()) for frame in conn.sent[:2]] == [
        {"type": "injection_ok"}, {"type": "injection_ok"}
    ]
    assert [status for status, _ in statuses] == [
        "Key event received", "Injection successful",
        "Key event received", "Injection successful",
        "Listening",
    ]
    assert active == [True, True]
