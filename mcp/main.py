#!/usr/bin/env python3
"""
Code Knowledge Graph MCP Server

Provides tools for querying and analyzing code relationships through the Model Context Protocol.
"""

import sys
import logging
import click
import anyio
from mcp.server_app import create_server

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
    force=True
)
logger = logging.getLogger("code_graph_mcp")

logger.error("Starting Code Knowledge Graph MCP Server")

@click.command()
@click.option("--graph-file", default="graph.json", help="Path to the graph.json file")
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(graph_file: str, port: int, transport: str) -> int:
    """Main entry point for the MCP server"""
    server = create_server(graph_file)
    
    if transport == "sse":
        server.run_sse(port)
    else:
        anyio.run(server.run_stdio)
    
    return 0

if __name__ == '__main__':
    main()
