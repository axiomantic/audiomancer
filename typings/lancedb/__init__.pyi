"""Type stubs for lancedb library.

Source: Local stubs (minimal for import resolution)
Created: 2026-01-01
Note: Basic stubs to resolve import errors. Expand as needed.
"""

from typing import Any

def connect(uri: str) -> Any: ...
def table(name: str, data: Any | None = None) -> Any: ...

class Table:
    def add(self, data: Any) -> None: ...
    def search(self, query: Any) -> Any: ...
