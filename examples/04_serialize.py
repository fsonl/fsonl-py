"""Serialize entries to FSONL text."""
import fsonl

schema = fsonl.Schema.from_string(
    "@schema log(level: string, msg: string)"
)

print(fsonl.dumps({"type": "log", "level": "info", "msg": "hello"}, schema=schema))
# @schema log(level: string, msg: string)
# log("info", "hello")
