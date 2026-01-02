"""Type stubs for mcp.types."""
from typing import Any, Dict

class Tool:
    name: str
    description: str
    inputSchema: Dict[str, Any]

    def __init__(self, *, name: str, description: str, inputSchema: Dict[str, Any]) -> None: ...

class TextContent:
    type: str
    text: str

    def __init__(self, *, type: str, text: str) -> None: ...

class ServerCapabilities:
    pass

class ToolsCapability:
    pass
