"""Windows low-level hook. F1/F2/F12 are always consumed and reserved."""
import ctypes
import logging
import threading
from ctypes import wintypes

log = logging.getLogger(__name__)


class KeyboardController:
    def __init__(self, event_callback, control_callback):
        self.event_callback = event_callback
        self.control_callback = control_callback
        self.mode = "LOCAL"
        self.running = False
        self.thread = None
        self.hook = None
        self._ready = threading.Event()
        self._startup_error = None
        self.held = set()
        self.lock = threading.Lock()

    def start(self):
        if self.running:
            return
        if __import__("os").name != "nt":
            raise OSError("Keyboard capture requires Windows")
        self.running = True
        self._ready.clear()
        self._startup_error = None
        self.thread = threading.Thread(target=self._message_loop, daemon=True)
        self.thread.start()
        if not self._ready.wait(3):
            self.running = False
            raise TimeoutError("Windows keyboard hook did not start in time")
        if self._startup_error:
            self.running = False
            raise self._startup_error

    def set_mode(self, mode):
        with self.lock:
            old = self.mode
            self.mode = mode
            if old == "REMOTE" and mode != "REMOTE":
                held = list(self.held)
                self.held.clear()
            else:
                held = []
        for key in held:
            self.event_callback("up", key)

    def stop(self):
        self.set_mode("LOCAL")
        self.running = False
        if self.thread and __import__("os").name == "nt":
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)

    def _message_loop(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
        kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
        self.thread_id = kernel32.GetCurrentThreadId()
        WH_KEYBOARD_LL, WM_QUIT = 13, 0x0012
        WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0100, 0x0101, 0x0104, 0x0105
        LRESULT = ctypes.c_ssize_t
        HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
        user32.SetWindowsHookExW.restype = wintypes.HANDLE
        user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
        user32.CallNextHookEx.restype = LRESULT
        user32.CallNextHookEx.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        def proc(ncode, wparam, lparam):
            if ncode >= 0 and wparam in (WM_KEYDOWN, WM_SYSKEYDOWN, WM_KEYUP, WM_SYSKEYUP):
                info = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = int(info.vkCode)
                key = _vk_to_key(vk, int(info.scanCode))
                down = wparam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                # SendInput events from the Client also traverse this hook
                # during same-machine testing. Let them reach the focused app
                # without forwarding them back across the TCP connection.
                if _is_injected(int(info.flags)):
                    return user32.CallNextHookEx(self.hook, ncode, wparam, lparam)
                if vk in (0x70, 0x71, 0x7B):
                    if down:
                        self.control_callback({0x70: "F1", 0x71: "F2", 0x7B: "F12"}[vk])
                    return 1
                with self.lock:
                    remote = self.mode == "REMOTE"
                    if remote and key:
                        if down:
                            self.held.add(key)
                        else:
                            self.held.discard(key)
                if remote:
                    if key:
                        try:
                            self.event_callback("down" if down else "up", key)
                        except Exception as exc:
                            log.warning("Could not queue keyboard event: %s", exc)
                    return 1
            return user32.CallNextHookEx(self.hook, ncode, wparam, lparam)
        self._proc = HOOKPROC(proc)
        try:
            self.hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
            if not self.hook:
                raise ctypes.WinError()
            self._ready.set()
        except Exception as exc:
            self._startup_error = exc
            self.running = False
            self._ready.set()
            return
        msg = wintypes.MSG()
        while self.running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg)); user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnhookWindowsHookEx(self.hook)
        self.hook = None


def _vk_to_key(vk, scan):
    names = {0x08:"BACKSPACE",0x09:"TAB",0x0D:"ENTER",0x10:"SHIFT",0x11:"CTRL",0x12:"ALT",0x13:"PAUSE",0x14:"CAPSLOCK",0x1B:"ESC",0x20:"SPACE",0x21:"PAGEUP",0x22:"PAGEDOWN",0x23:"END",0x24:"HOME",0x25:"LEFT",0x26:"UP",0x27:"RIGHT",0x28:"DOWN",0x2C:"PRINTSCREEN",0x2D:"INSERT",0x2E:"DELETE",0x5B:"LWIN",0x5C:"RWIN",0x90:"NUMLOCK",0x91:"SCROLLLOCK",0xA0:"LSHIFT",0xA1:"RSHIFT",0xA2:"LCTRL",0xA3:"RCTRL",0xA4:"LALT",0xA5:"RALT",0x6A:"MULTIPLY",0x6B:"ADD",0x6D:"SUBTRACT",0x6E:"DECIMAL",0x6F:"DIVIDE",0xBA:"SEMICOLON",0xBB:"EQUALS",0xBC:"COMMA",0xBD:"MINUS",0xBE:"PERIOD",0xBF:"SLASH",0xC0:"GRAVE",0xDB:"LBRACKET",0xDC:"BACKSLASH",0xDD:"RBRACKET",0xDE:"QUOTE"}
    names.update({0x30+i:str(i) for i in range(10)})
    names.update({0x41+i:chr(0x41+i) for i in range(26)})
    names.update({0x60+i:f"NUMPAD{i}" for i in range(10)})
    if 0x70 <= vk <= 0x87:
        return f"F{vk-0x6F}"
    return names.get(vk)


def _is_injected(flags):
    return bool(flags & 0x10)  # LLKHF_INJECTED
