"""
Server initialization and transport handling for the Code Knowledge Graph MCP Server
"""

import sys
import logging
import anyio
from typing import Optional, Tuple, AsyncGenerator
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.graph_manager import GraphManager
from mcp.tools import get_tool_definitions, handle_tool_call

logger = logging.getLogger("code_graph_mcp.server")

class ServerApp:
    """Main server application class that handles initialization and transport"""
    
    def __init__(self, graph_file: str):
        """Initialize the server with a graph file"""
        self.graph: Optional[GraphManager] = None
        self.app = Server("Code Knowledge Graph")
        self.graph_file = graph_file
        
        # Register handlers
        self.app.list_tools()(self._list_tools)
        self.app.call_tool()(self._call_tool)
    
    async def _list_tools(self):
        """Handler for listing available tools"""
        return get_tool_definitions()
    
    async def _call_tool(self, name: str, arguments: dict):
        """Handler for tool calls"""
        return await handle_tool_call(name, arguments, self.graph)
    
    def initialize(self) -> None:
        """Initialize the graph manager"""
        print(f"Starting server with graph file: {self.graph_file}", file=sys.stderr)
        try:
            self.graph = GraphManager(self.graph_file)
        except Exception as e:
            print(f"Error loading graph file: {e}", file=sys.stderr)
            raise
        print("Server initialization complete", file=sys.stderr)
    
    async def run_stdio(self) -> None:
        """Run the server with stdio transport"""
        async with stdio_server() as streams:
            await self.app.run(
                streams[0], streams[1], self.app.create_initialization_options()
            )
    
    def run_sse(self, port: int = 8000) -> None:
        """Run the server with SSE transport"""
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        
        sse = SseServerTransport("/messages/")
        
        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self.app.run(
                    streams[0], streams[1], self.app.create_initialization_options()
                )
        
        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )
        
        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=port)

def create_server(graph_file: str) -> ServerApp:
    """Create and initialize a new server instance"""
    server = ServerApp(graph_file)
    server.initialize()
    return server 