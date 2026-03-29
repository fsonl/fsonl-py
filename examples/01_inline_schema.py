"""Parse with inline schema."""
import fsonl

text = """\
@schema rm(target: string, --force?: bool = false)
rm("tmp.log")
rm("/var/cache", force=true)
"""

result = fsonl.loads(text)
for entry in result.entries:
    print(entry)
# {'type': 'rm', 'target': 'tmp.log', 'force': False}
# {'type': 'rm', 'target': '/var/cache', 'force': True}
