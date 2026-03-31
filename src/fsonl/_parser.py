"""Stage 1 parser: parse FSONL text into entry dicts and SchemaDirective lists."""

from ._errors import ParseError, SchemaError
from ._scanner import skip_ws, read_identifier, looks_like_identifier, _is_ident_start
from ._values import parse_value
from ._schema_parser import parse_schema_line


def parse_document_items(text):
    """Parse a full FSONL document, yielding items in document order.
    Yields entry dict and SchemaDirective interleaved in line order.
    Validates @schema ordering (must appear before entries of that type)
    and duplicate @schema declarations.
    """
    yield from _parse_items(_prepare_lines(text))


def _prepare_lines(text):
    """Convert text to (line_number, cleaned_line) pairs."""
    if text and text[0] == '\uFEFF':
        text = text[1:]

    raw_lines = text.split('\n')

    for i, raw_line in enumerate(raw_lines):
        line_number = i + 1

        if raw_line.endswith('\r'):
            is_last_line = (i == len(raw_lines) - 1)
            if is_last_line and not text.endswith('\n'):
                raise ParseError(line_number, "Bare \\r is not allowed")
            line = raw_line[:-1]
        else:
            line = raw_line

        if '\r' in line:
            raise ParseError(line_number, "Bare \\r is not allowed")

        yield (line_number, line)


def _prepare_file_lines(file_obj):
    """Convert file object to (line_number, cleaned_line) pairs for streaming."""
    for i, raw_line in enumerate(file_obj):
        line_number = i + 1

        has_newline = raw_line.endswith('\n')
        if has_newline:
            raw_line = raw_line[:-1]

        if raw_line.endswith('\r'):
            if has_newline:
                # Was \r\n, safe to strip
                line = raw_line[:-1]
            else:
                # Bare \r (no \n after it)
                raise ParseError(line_number, "Bare \\r is not allowed")
        else:
            line = raw_line

        if '\r' in line:
            raise ParseError(line_number, "Bare \\r is not allowed")

        if i == 0 and line and line[0] == '\uFEFF':
            line = line[1:]

        yield (line_number, line)


def _parse_items(numbered_lines):
    """Core parser: yield entry dict/SchemaDirective from (line_number, line) pairs.
    Validates @schema ordering and duplicate declarations.
    """
    schema_names = {}   # type_name → line_number (for duplicate detection)
    entry_types = {}    # type_name → first line_number (for ordering check)

    for line_number, line in numbered_lines:
        # Skip empty lines
        pos = skip_ws(line, 0)
        if pos >= len(line):
            continue

        # Check for comment
        if line[pos:pos + 2] == '//':
            continue

        # Check for @schema
        if line[pos:pos + 7] == '@schema':
            if pos + 7 >= len(line) or line[pos + 7] not in (' ', '\t'):
                raise ParseError(line_number, "Incomplete @schema directive")
            directive = parse_schema_line(line, pos + 7, line_number)

            # Check duplicate @schema
            if directive.name in schema_names:
                raise SchemaError(line_number, f"Duplicate @schema for type '{directive.name}'")
            schema_names[directive.name] = line_number

            # Check ordering: @schema must come before entries of that type
            if directive.name in entry_types:
                raise SchemaError(line_number, f"@schema for '{directive.name}' appears after entry at line {entry_types[directive.name]}")

            yield directive
            continue

        # Otherwise it's an entry
        entry = _parse_entry(line, pos, line_number)
        if entry["type"] not in entry_types:
            entry_types[entry["type"]] = line_number
        yield entry


def _parse_entry(line, pos, line_number):
    """Parse a single entry line starting at pos."""
    # Read type name
    if not (pos < len(line) and _is_ident_start(line[pos])):
        raise ParseError(line_number, f"Expected type name at position {pos}")

    type_name, pos = read_identifier(line, pos, line_number)

    # Expect '(' immediately (no space between type name and paren)
    if pos >= len(line) or line[pos] != '(':
        raise ParseError(line_number, "Expected '(' immediately after type name")
    pos += 1  # consume '('

    # Parse argument list
    positional, named, pos = _parse_args(line, pos, line_number)

    # Expect ')'
    if pos >= len(line) or line[pos] != ')':
        raise ParseError(line_number, "Expected ')'")
    pos += 1  # consume ')'

    # Check trailing
    _check_trailing(line, pos, line_number)

    return {"type": type_name, "positional": positional, "named": named, "_line": line_number}


def _parse_args(line, pos, line_number):
    """Parse argument list between ( and ).
    Returns (positional, named, pos) where pos points to ')'.
    """
    positional = []
    named = {}
    seen_named = False

    pos = skip_ws(line, pos)

    # Empty args
    if pos < len(line) and line[pos] == ')':
        return positional, named, pos

    while True:
        pos = skip_ws(line, pos)

        # Check for // inside arg list (error)
        if pos < len(line) and line[pos:pos + 2] == '//':
            raise ParseError(line_number, "Comments not allowed inside argument list")

        # Try NamedArg: identifier '=' value
        if looks_like_identifier(line, pos):
            saved_pos = pos
            ident, pos2 = read_identifier(line, pos, line_number)
            pos2 = skip_ws(line, pos2)
            if pos2 < len(line) and line[pos2] == '=':
                # NamedArg confirmed
                key = ident
                if key == "type":
                    raise ParseError(line_number, "'type' is reserved")
                if key in named:
                    raise ParseError(line_number, f"Duplicate named argument '{key}'")
                pos2 = skip_ws(line, pos2 + 1)
                # Check for empty value after =
                if pos2 >= len(line) or line[pos2] == ')' or line[pos2] == ',':
                    raise ParseError(line_number, f"Expected value after '='")
                value, pos2 = parse_value(line, pos2, line_number)
                named[key] = value
                seen_named = True
                pos = pos2
            else:
                # Not a NamedArg, fallback to Value
                pos = saved_pos
                if seen_named:
                    raise ParseError(line_number, "Positional argument after named argument")
                value, pos = parse_value(line, pos, line_number)
                positional.append(value)
        else:
            # Not an identifier, must be a Value
            if seen_named:
                raise ParseError(line_number, "Positional argument after named argument")
            value, pos = parse_value(line, pos, line_number)
            positional.append(value)

        pos = skip_ws(line, pos)

        if pos < len(line) and line[pos] == ',':
            pos += 1
            pos = skip_ws(line, pos)
            # Check for trailing comma
            if pos < len(line) and line[pos] == ')':
                raise ParseError(line_number, "Trailing comma")
            continue
        elif pos < len(line) and line[pos] == ')':
            break
        else:
            if pos >= len(line):
                raise ParseError(line_number, "Unclosed parenthesis")
            raise ParseError(line_number, f"Unexpected character '{line[pos]}' in argument list")

    return positional, named, pos


def _check_trailing(line, pos, line_number):
    """Check that only whitespace and // comments follow after ')'."""
    pos = skip_ws(line, pos)
    if pos >= len(line):
        return
    if line[pos:pos + 2] == '//':
        return
    raise ParseError(line_number, f"Unexpected content after ')'")
