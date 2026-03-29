"""Parse with code schema."""
import fsonl

schema = fsonl.Schema.from_string(
    "@schema log(level: string, msg: string)"
)

text = """\
log("info", "started")
"""

result = fsonl.loads(text, schema=schema)
print(result.entries[0])
# {'type': 'log', 'level': 'info', 'msg': 'started'}
