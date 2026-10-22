"""Small, bounded newline-delimited JSON protocol."""
import json

MAX_LINE = 4096
ALLOWED_KEYS = frozenset(
    [f"F{i}" for i in range(1, 25)]
    + ["ESC", "TAB", "CAPSLOCK", "SPACE", "ENTER", "BACKSPACE", "DELETE", "INSERT",
       "HOME", "END", "PAGEUP", "PAGEDOWN", "LEFT", "RIGHT", "UP", "DOWN",
       "SHIFT", "LSHIFT", "RSHIFT", "CTRL", "LCTRL", "RCTRL", "ALT", "LALT",
       "RALT", "LWIN", "RWIN", "A", "B", "C", "D", "E", "F", "G",
       "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
       "U", "V", "W", "X", "Y", "Z", "0", "1", "2", "3", "4", "5", "6",
       "7", "8", "9", "MINUS", "EQUALS", "LBRACKET", "RBRACKET", "BACKSLASH",
       "SEMICOLON", "QUOTE", "COMMA", "PERIOD", "SLASH", "GRAVE", "PRINTSCREEN",
       "SCROLLLOCK", "PAUSE", "NUMLOCK", "NUMPAD0", "NUMPAD1", "NUMPAD2",
       "NUMPAD3", "NUMPAD4", "NUMPAD5", "NUMPAD6", "NUMPAD7", "NUMPAD8",
       "NUMPAD9", "DECIMAL", "DIVIDE", "MULTIPLY", "SUBTRACT", "ADD"]
)


def encode(message):
    raw = json.dumps(message, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
    if len(raw) > MAX_LINE:
        raise ValueError("message too large")
    return raw


def decode_line(raw):
    if len(raw) > MAX_LINE:
        raise ValueError("message too large")
    try:
        message = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ValueError("message must be an object with a type")
    kind = message["type"]
    if kind == "auth":
        if set(message) != {"type", "token"} or not isinstance(message["token"], str) or not 8 <= len(message["token"]) <= 128:
            raise ValueError("invalid auth message")
    elif kind == "key":
        if set(message) != {"type", "action", "key"} or message["action"] not in ("down", "up") or message["key"] not in ALLOWED_KEYS:
            raise ValueError("invalid key event")
    elif kind == "injection_error":
        if set(message) != {"type", "detail"} or not isinstance(message["detail"], str) or len(message["detail"]) > 512:
            raise ValueError("invalid injection error")
    elif kind not in ("auth_ok", "injection_ok", "stop", "ping", "pong") or set(message) != {"type"}:
        raise ValueError("unsupported message")
    return message


class LineBuffer:
    """Extract complete newline-delimited messages, including split TCP frames."""
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, chunk):
        self.buffer.extend(chunk)
        messages = []
        while True:
            pos = self.buffer.find(b"\n")
            if pos < 0:
                if len(self.buffer) > MAX_LINE:
                    raise ValueError("message too large")
                break
            line = bytes(self.buffer[:pos])
            del self.buffer[:pos + 1]
            messages.append(decode_line(line))
        return messages
