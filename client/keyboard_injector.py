"""SendInput based keyboard injection; only virtual keys from the protocol allowlist."""
import ctypes
from ctypes import wintypes
import os

from shared.protocol import ALLOWED_KEYS

VK = {"BACKSPACE":0x08,"TAB":0x09,"ENTER":0x0D,"SHIFT":0x10,"CTRL":0x11,"ALT":0x12,"PAUSE":0x13,"CAPSLOCK":0x14,"ESC":0x1B,"SPACE":0x20,"PAGEUP":0x21,"PAGEDOWN":0x22,"END":0x23,"HOME":0x24,"LEFT":0x25,"UP":0x26,"RIGHT":0x27,"DOWN":0x28,"PRINTSCREEN":0x2C,"INSERT":0x2D,"DELETE":0x2E,"LWIN":0x5B,"RWIN":0x5C,"NUMLOCK":0x90,"SCROLLLOCK":0x91,"MINUS":0xBD,"EQUALS":0xBB,"LBRACKET":0xDB,"RBRACKET":0xDD,"BACKSLASH":0xDC,"SEMICOLON":0xBA,"QUOTE":0xDE,"COMMA":0xBC,"PERIOD":0xBE,"SLASH":0xBF,"GRAVE":0xC0,"ADD":0x6B,"SUBTRACT":0x6D,"MULTIPLY":0x6A,"DIVIDE":0x6F,"DECIMAL":0x6E}
VK.update({f"F{i}":0x6F+i for i in range(1,25)})
VK.update({f"NUMPAD{i}":0x60+i for i in range(10)})
VK.update({"LSHIFT":0xA0,"RSHIFT":0xA1,"LCTRL":0xA2,"RCTRL":0xA3,"LALT":0xA4,"RALT":0xA5})
VK.update({str(i):ord(str(i)) for i in range(10)})
VK.update({chr(i):i for i in range(ord('A'),ord('Z')+1)})


ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


class KeyboardInjector:
    def __init__(self):
        self.held = set()

    def event(self, action, key):
        if action not in ("down", "up") or not isinstance(key, str) or key not in ALLOWED_KEYS:
            raise ValueError("Invalid keyboard event")
        if os.name != "nt":
            raise OSError("Keyboard injection requires Windows")
        vk = VK.get(key)
        if vk is None:
            raise ValueError("Unsupported key")
        self._send(vk, action == "up")
        if action == "down":
            self.held.add(key)
        else:
            self.held.discard(key)

    def release_all(self):
        held, self.held = tuple(self.held), set()
        if os.name != "nt":
            return
        errors = []
        for key in held:
            vk = VK.get(key)
            if vk is not None:
                try:
                    self._send(vk, True)
                except OSError as exc:
                    errors.append(exc)
        if errors:
            raise OSError("Could not release all remotely held keys: " + "; ".join(map(str, errors)))

    @staticmethod
    def _send(vk, keyup):
        extended = vk in {0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x2D,0x2E,0x5B,0x5C,0x6F,0xA3,0xA5}
        flags = (0x0002 if keyup else 0) | (0x0001 if extended else 0)
        item = INPUT(type=1, ki=KEYBDINPUT(vk, 0, flags, 0, 0))
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        send_input = user32.SendInput
        send_input.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        send_input.restype = wintypes.UINT
        ctypes.set_last_error(0)
        inserted = send_input(1, ctypes.byref(item), ctypes.sizeof(INPUT))
        if inserted != 1:
            error = ctypes.get_last_error()
            if error:
                raise ctypes.WinError(error)
            raise OSError("SendInput inserted no keyboard events")
