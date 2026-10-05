from typing import Callable, Dict, Any

class MCPServer:
    """
    Lightweight Model Context Protocol (MCP) server implementation for DevGuard developer tools.
    """
    def __init__(self, name: str):
        self.name = name
        self._tools: Dict[str, Callable] = {}

    def tool(self) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._tools[func.__name__] = func
            return func
        return decorator

    def run(self, transport: str = "stdio"):
        print(f"[{self.name}] Server running on {transport} transport.")
