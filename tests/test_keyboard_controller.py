import queue
from types import SimpleNamespace

from host.gui import HostApp
from host.keyboard_controller import KeyboardController, _is_injected, _vk_to_key


def test_control_keys_map_but_are_outside_key_event_path():
    assert _vk_to_key(0x41,0)=="A"
    assert _vk_to_key(0x70,0)=="F1"


def test_mode_release_tracks_held_remote_keys():
    events=[]; ctl=KeyboardController(lambda action,key:events.append((action,key)),lambda key:None)
    ctl.mode="REMOTE"; ctl.held={"SHIFT","A"}; ctl.set_mode("LOCAL")
    assert set(events)=={("up","SHIFT"),("up","A")}
    assert not ctl.held


def test_injected_events_are_identified_for_feedback_loop_prevention():
    assert _is_injected(0x10)
    assert not _is_injected(0)
    assert not _is_injected(0x20)


def test_f1_f2_and_f12_select_local_remote_and_local():
    selected = []
    app = HostApp.__new__(HostApp)
    app.network = SimpleNamespace(sock=object())
    app.controller = SimpleNamespace(set_mode=selected.append)
    app.events = queue.Queue()

    for key in ("F1", "F2", "F12"):
        app._switch_from_hook(key)

    assert selected == ["LOCAL", "REMOTE", "LOCAL"]
    queued = [app.events.get_nowait() for _ in range(6)]
    assert [event for event in queued if event[0] == "mode"] == [
        ("mode", "LOCAL"), ("mode", "REMOTE"), ("mode", "LOCAL")
    ]
    assert [event[1] for event in queued if event[0] == "status"] == [
        "Local mode selected; forwarding stopped",
        "Remote mode selected; Client connected; waiting for injection confirmation",
        "Local mode selected; forwarding stopped",
    ]


def test_f2_without_authenticated_connection_stays_local():
    selected = []
    app = HostApp.__new__(HostApp)
    app.network = SimpleNamespace(sock=None)
    app.controller = SimpleNamespace(set_mode=selected.append)
    app.events = queue.Queue()

    app._switch_from_hook("F2")

    assert selected == ["LOCAL"]
    assert app.events.get_nowait() == (
        "status", "Remote mode not selected; connect and authenticate the Client first"
    )
    assert app.events.get_nowait() == ("mode", "LOCAL")
