"""Raw mode (no schema binding)."""
import fsonl

text = """\
x(1, "hello", flag=true)
"""

result = fsonl.loads_raw(text)
entry = result[0]
print(entry["type"])        # 'x'
print(entry["positional"])  # [1, 'hello']
print(entry["named"])       # {'flag': True}
