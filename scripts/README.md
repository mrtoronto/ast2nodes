# Scripts Directory

This directory contains utility scripts for working with the code parser and knowledge graph tools.

## Available Scripts

### `parse_local_files.py`
Parses a local codebase and generates a knowledge graph in JSON format.

```bash
python scripts/parse_local_files.py /path/to/your/codebase --output code_graph.json
```

### `visualize_graph.py`
Creates an interactive visualization of a code knowledge graph.

```bash
python scripts/visualize_graph.py code_graph.json

# Options:
-e, --entity-types    Filter by entity types (e.g., class function)
-r, --relationships   Filter by relationship types (e.g., defines uses calls)
-m, --max-nodes      Limit number of nodes
-o, --output         Custom output file path
```

### `generate_mcp_config.py`
Generates an MCP configuration file for using the code knowledge graph in your project.

```bash
# Print configuration to stdout
./scripts/generate_mcp_config.py /absolute/path/to/graph.json

# Save directly to .cursor/mcp.json
./scripts/generate_mcp_config.py /absolute/path/to/graph.json -o .cursor/mcp.json
```

Options:
- `graph_path`: (Required) Absolute path to the knowledge graph file
- `-o, --output`: Output path for mcp.json (optional, defaults to stdout)

The generated configuration will set up the code knowledge graph server for use with your project. 