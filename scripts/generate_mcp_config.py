#!/usr/bin/env python3
"""
Script to generate mcp.json configuration file for code knowledge graph server.
Takes a knowledge graph file path and generates appropriate mcp.json config.
"""

import os
import json
import argparse
from pathlib import Path

def generate_mcp_config(graph_path: str, output_path: str = None) -> None:
    """
    Generate mcp.json configuration for the code knowledge graph server.
    
    Args:
        graph_path: Absolute path to the knowledge graph file
        output_path: Optional path to write the config. If not provided, prints to stdout.
    """
    # Convert to absolute path if not already
    graph_path = os.path.abspath(graph_path)
    
    # Create the config structure
    config = {
        "mcpServers": {
            "code_graph": {
                "command": "./venv/bin/python",
                "args": [
                    "./mcp/main.py",
                    "--graph-file",
                    graph_path
                ],
                "description": "An MCP server to intelligently search through a codebase using a knowledge graph"
            }
        }
    }
    
    # Convert to JSON with pretty printing
    config_json = json.dumps(config, indent=2)
    
    if output_path:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(config_json)
        print(f"Configuration written to {output_path}")
    else:
        # Print to stdout
        print(config_json)

def main():
    parser = argparse.ArgumentParser(description="Generate mcp.json configuration for code knowledge graph server")
    parser.add_argument("graph_path", help="Absolute path to the knowledge graph file")
    parser.add_argument("-o", "--output", help="Output path for mcp.json (optional, defaults to stdout)")
    
    args = parser.parse_args()
    generate_mcp_config(args.graph_path, args.output)

if __name__ == "__main__":
    main() 