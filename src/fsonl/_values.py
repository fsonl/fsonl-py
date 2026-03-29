import json
import math

from ._errors import ParseError
from ._scanner import skip_ws


def parse_value(line, pos, line_number):
    """Parse a JSON value starting at pos. Returns (value, end_pos)."""
    pos = skip_ws(line, pos)
    if pos >= len(line):
        raise ParseError(line_number, "Expected value but reached end of line")

    ch = line[pos]

    if ch == '"':
        raw, end = extract_string(line, pos, line_number)
    elif ch == '[' or ch == '{':
        raw, end = extract_bracketed(line, pos, line_number)
    else:
        raw, end = extract_token(line, pos, line_number)

    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ParseError(line_number, f"Invalid value: {raw!r} ({e})")

    # Reject non-finite floats (Infinity, NaN) — not valid JSON values
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        raise ParseError(line_number, f"Number out of range: {raw!r}")

    return value, end


def extract_string(line, pos, line_number):
    """Extract a JSON string including quotes. Returns (raw, end_pos)."""
    if line[pos] != '"':
        raise ParseError(line_number, f"Expected '\"' at position {pos}")
    i = pos + 1

    while i < len(line):
        ch = line[i]
        if ch == '\\':
            i += 2
            continue
        if ch == '"':
            return line[pos:i + 1], i + 1
        i += 1

    raise ParseError(line_number, "Unclosed string")


_BRACKET_PAIRS = {'[': ']', '{': '}'}

def extract_bracketed(line, pos, line_number):
    """Extract a bracketed value (array or object) with bracket-type matching."""
    stack = []
    in_string = False
    i = pos

    while i < len(line):
        ch = line[i]

        if in_string:
            if ch == '\\':
                i += 2
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in _BRACKET_PAIRS:
                stack.append((ch, i))
            elif ch == ']' or ch == '}':
                if not stack:
                    raise ParseError(line_number, f"Unexpected '{ch}' at position {i}")
                opener, open_pos = stack.pop()
                expected = _BRACKET_PAIRS[opener]
                if ch != expected:
                    raise ParseError(line_number, f"Mismatched bracket: '{opener}' at position {open_pos} closed by '{ch}' at position {i}")
                if not stack:
                    return line[pos:i + 1], i + 1

        i += 1

    raise ParseError(line_number, "Unclosed bracket")


def extract_token(line, pos, line_number):
    """Extract a token (number, bool, null) until delimiter."""
    i = pos

    while i < len(line):
        ch = line[i]
        if ch in (',', ')', ']', '}', ' ', '\t'):
            break
        i += 1

    if i == pos:
        raise ParseError(line_number, f"Empty token at position {pos}")

    raw = line[pos:i]
    return raw, i
