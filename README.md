# FSONL

**Function-Styled Object Notation Lines**

A line-based serialization format where each record's type is immediately visible at the start of the line.

```
@schema rm(target: string, --force?: bool = false)
rm("tmp.log", force=true)
rm("/var/cache", force=false)
log("info", "server started")
```

## Install

```bash
pip install fsonl
```

## Quick Start

### Parse with inline schema

```python
import fsonl

text = """
@schema rm(target: string, --force?: bool = false)
rm("tmp.log")
rm("/var/cache", force=true)
"""

result = fsonl.loads(text)
for entry in result.entries:
    print(entry)
# {'type': 'rm', 'target': 'tmp.log', 'force': False}
# {'type': 'rm', 'target': '/var/cache', 'force': True}
```

### Parse with code schema

```python
import fsonl

schema = fsonl.Schema.from_string(
    "@schema log(level: string, msg: string)"
)

result = fsonl.loads('log("info", "started")\n', schema=schema)
print(result.entries[0])
# {'type': 'log', 'level': 'info', 'msg': 'started'}
```

### Define schema from Python functions (3.10+)

```python
import fsonl

schema = fsonl.Schema()

@schema.define
def rm(target: str, *, force: bool = False): ...

result = fsonl.loads('rm("tmp.log", force=true)\n', schema=schema)
print(result.entries[0])
# {'type': 'rm', 'target': 'tmp.log', 'force': True}
```

### Serialize

```python
import fsonl

schema = fsonl.Schema.from_string(
    "@schema log(level: string, msg: string)"
)

print(fsonl.dumps([{"type": "log", "level": "info", "msg": "hello"}], schema=schema))
# @schema log(level: string, msg: string)
# log("info", "hello")
```

### Stream from file

```python
import fsonl

with open("events.fsonl", newline="") as f:
    for entry in fsonl.iter_entries(f):
        print(entry)
```

### Raw mode (no schema binding)

```python
import fsonl

result = fsonl.loads_raw('x(1, "hello", flag=true)\n')
entry = result[0]
print(entry["type"])        # 'x'
print(entry["positional"])  # [1, 'hello']
print(entry["named"])       # {'flag': True}
```

## API

### Parsing

| Function | Description |
|----------|-------------|
| `loads(text, *, schema, ignore_inline_schema, extra_fields)` | Parse FSONL text with schema binding |
| `load(fp, **kwargs)` | Parse from file object with schema binding |
| `loads_raw(text)` | Parse FSONL text without binding (Stage 1 only) |
| `load_raw(fp)` | Parse from file object without binding (Stage 1 only) |
| `iter_entries(source, *, schema, ignore_inline_schema, extra_fields)` | Lazy iterator over bound entries |
| `iter_raw(source)` | Lazy iterator over raw entries |
| `bind(entry, schema, *, line, extra_fields)` | Bind a single raw dict to a Schema |

### Serialization

| Function | Description |
|----------|-------------|
| `dumps(entries, *, schema, allow_extra, exclude_schema)` | Serialize to FSONL text |
| `dump(entries, fp, *, schema, allow_extra, exclude_schema)` | Serialize to file object |

### Schema

| Method | Description |
|--------|-------------|
| `Schema.from_string(text)` | Create from `@schema` lines |
| `Schema.from_fsonl(text)` | Extract `@schema` from FSONL text (non-schema lines ignored) |
| `Schema.from_file(path)` | Load `@schema` from a `.fsonl` file |
| `@schema.define` | Decorator: define schema from function signature (Python 3.10+) |
| `schema.add(text)` | Add more `@schema` definitions |
| `schema.get(type_name)` | Look up a type definition |
| `schema.has(type_name)` | Check if a type is defined |
| `schema.type_names()` | List all defined type names |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `ignore_inline_schema` | `False` | Skip `@schema` directives in the content |
| `allow_extra` | `False` | (`dumps` only) Ignore extra keys not in schema |
| `exclude_schema` | `False` | (`dumps` only) Omit `@schema` lines from output |
| `extra_fields` | `ExtraFieldPolicy.ERROR` | Policy for undeclared named arguments |

### Errors

All errors include line numbers: `str(error)` produces `"line 42: message"`.

| Exception | Kind | Stage |
|-----------|------|-------|
| `ParseError` | `syntax_error` | Stage 1 (syntax parse) |
| `SchemaError` | `schema_error` | Schema definition / cross-validation |
| `BindError` | `bind_error` | Stage 2 (data vs schema mismatch) |

All inherit from `FsonlError`, which inherits from `Exception`.

## Schema Types

```
string          -- JSON string
number          -- JSON number (int or float)
bool            -- true / false
null            -- null
any             -- any JSON value
string[]        -- array of strings
(string | number)[]  -- array of union
{ cmd: string, id?: number }  -- fixed-shape object
string | null   -- nullable string
```

## CLI

```bash
# Parse with schema binding (default)
echo '@schema x(a: number)\nx(1)' | python -m fsonl parse

# Raw parse (no binding)
echo 'x(1)' | python -m fsonl parse --raw

# Extract @schema directives only
echo '@schema x(a: number)\nx(1)' | python -m fsonl parse --schema
```

## Format Overview

- One entry per line: `type(args)`
- Values are JSON literals: strings, numbers, booleans, null, arrays, objects
- Positional args come before named args: `log("info", tag="v2")`
- Comments: `// ...` (outside argument lists only)
- File extension: `.fsonl`, MIME: `text/fsonl`, encoding: UTF-8

## Specification

- [SPEC.ko.md](https://github.com/fsonl/fsonl/blob/main/spec/SPEC.ko.md) -- Language specification (Korean)
- [GRAMMAR.ko.peg](https://github.com/fsonl/fsonl/blob/main/spec/GRAMMAR.ko.peg) -- PEG formal grammar (Korean)

## License

MIT
