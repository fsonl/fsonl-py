"""Define schema from Python functions (3.10+)."""
import fsonl

schema = fsonl.Schema()

@schema.define
def rm(target: str, *, force: bool = False): ...

text = """\
rm("tmp.log", force=true)
"""

result = fsonl.loads(text, schema=schema)
print(result.entries[0])
# {'type': 'rm', 'target': 'tmp.log', 'force': True}
