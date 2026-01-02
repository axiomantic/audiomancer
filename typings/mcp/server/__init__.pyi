"""Type stubs for mcp.server."""
from typing import Callable, TypeVar, Any, Awaitable
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

_T = TypeVar("_T")

class Server:
    def __init__(self, name: str) -> None: ...

    def list_tools(self) -> Callable[[Callable[[], Awaitable[list[Tool]]]], Callable[[], Awaitable[list[Tool]]]]: ...

    def call_tool(self) -> Callable[[Callable[[str, dict[str, Any]], Awaitable[list[TextContent]]]], Callable[[str, dict[str, Any]], Awaitable[list[TextContent]]]]: ...
