from __future__ import annotations


class FsonlError(Exception):
    def __init__(self, kind: str, line: int, message: str) -> None:
        self.kind = kind
        self.line = line
        self.message = message
        super().__init__(kind, line, message)

    def __str__(self) -> str:
        return f"line {self.line}: {self.message}"

    def __reduce__(self):
        return (self.__class__, (self.kind, self.line, self.message))


class ParseError(FsonlError):
    def __init__(self, line: int, message: str) -> None:
        super().__init__("syntax_error", line, message)

    def __reduce__(self):
        return (self.__class__, (self.line, self.message))


class SchemaError(FsonlError):
    def __init__(self, line: int, message: str) -> None:
        super().__init__("schema_error", line, message)

    def __reduce__(self):
        return (self.__class__, (self.line, self.message))


class BindError(FsonlError):
    def __init__(self, line: int, message: str) -> None:
        super().__init__("bind_error", line, message)

    def __reduce__(self):
        return (self.__class__, (self.line, self.message))
