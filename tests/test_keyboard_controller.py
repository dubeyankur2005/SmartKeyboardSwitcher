from host.keyboard_controller import KeyboardController, _vk_to_key


def test_control_keys_map_but_are_outside_key_event_path():
    assert _vk_to_key(0x41,0)=="A"
    assert _vk_to_key(0x70,0)=="F1"


def test_mode_release_tracks_held_remote_keys():
    events=[]; ctl=KeyboardController(lambda action,key:events.append((action,key)),lambda key:None)
    ctl.mode="REMOTE"; ctl.held={"SHIFT","A"}; ctl.set_mode("LOCAL")
    assert set(events)=={("up","SHIFT"),("up","A")}
    assert not ctl.held
