"""Stream from file."""
import fsonl
import tempfile
import os

# Create a temp .fsonl file
content = """\
@schema rm(target: string, --force?: bool = false)
rm("tmp.log")
rm("/cache", force=true)
"""
fd, path = tempfile.mkstemp(suffix=".fsonl")
os.close(fd)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

with open(path, newline="") as f:
    for entry in fsonl.iter_entries(f):
        print(entry)
# {'type': 'rm', 'target': 'tmp.log', 'force': False}
# {'type': 'rm', 'target': '/cache', 'force': True}

os.unlink(path)
