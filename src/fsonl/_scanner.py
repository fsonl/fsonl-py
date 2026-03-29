from ._errors import ParseError


def skip_ws(line, pos):
    """Skip spaces and tabs."""
    while pos < len(line) and line[pos] in (' ', '\t'):
        pos += 1
    return pos


def _is_ident_start(ch):
    """Check if character can start an identifier [a-zA-Z_]."""
    return ch == '_' or ('a' <= ch <= 'z') or ('A' <= ch <= 'Z')


def _is_ident_char(ch):
    """Check if character can continue an identifier [a-zA-Z0-9_]."""
    return ch == '_' or ('a' <= ch <= 'z') or ('A' <= ch <= 'Z') or ('0' <= ch <= '9')


def read_identifier(line, pos, line_number):
    """Read an identifier [a-zA-Z_][a-zA-Z0-9_]*. Raises ParseError if none found."""
    start = pos
    if pos < len(line) and _is_ident_start(line[pos]):
        pos += 1
        while pos < len(line) and _is_ident_char(line[pos]):
            pos += 1
    if pos == start:
        raise ParseError(line_number, f"Expected identifier at position {pos}")
    return line[start:pos], pos


def looks_like_identifier(line, pos):
    """Check if position starts with [a-zA-Z_]."""
    return pos < len(line) and _is_ident_start(line[pos])


def expect(line, pos, char, line_number):
    """Expect a specific character at pos. Returns pos+1."""
    if pos >= len(line) or line[pos] != char:
        raise ParseError(line_number, f"Expected '{char}' at position {pos}")
    return pos + 1
