# Code Knowledge Graph

A tool for building and analyzing knowledge graphs from your codebase. Extract relationships between code entities, understand dependencies, and gain insights through intelligent code analysis.

## Overview

The Code Knowledge Graph tool analyzes your codebase to build a comprehensive graph of code relationships. It supports multiple languages (Python, JavaScript, HTML, CSS) and provides intelligent analysis through MCP (Machine Comprehension Protocol) integration.

## Key Features

- **Multi-Language Support**: Analyze Python, JavaScript, HTML, and CSS files
- **Relationship Extraction**: Map dependencies, calls, inheritance, and more
- **Intelligent Analysis**: Search code semantically, track dependencies, analyze impact
- **Interactive Visualization**: Explore code relationships visually
- **MCP Integration**: Use the knowledge graph in your IDE through MCP

## Getting Started

1. Install the tool:
```bash
# Clone the repository
git clone https://github.com/mrtoronto/ast2nodes.git
cd code-kgs

# Install dependencies
pip install -r requirements.txt
```

2. Generate a knowledge graph from your codebase:
```bash
python scripts/parse_local_files.py /path/to/your/codebase --output graph.json
```

Or parse a git repository:

```bash
python scripts/parse_git_repo.py https://github.com/mrtoronto/flask-demo
```

3. Set up MCP integration:
```bash
# Generate MCP configuration
./scripts/generate_mcp_config.py /absolute/path/to/graph.json -o .cursor/mcp.json
```

4. Start using the knowledge graph in your IDE through MCP for:
- Semantic code search
- Dependency analysis
- Impact analysis
- Code path exploration
- Dead code detection

## Documentation

- [MCP Integration Guide](docs/mcp_integration.md): Detailed guide on using the knowledge graph in your IDE
- [Scripts Documentation](scripts/README.md): Available utility scripts and their usage
- [Testing Documentation](tests/README.md): Information about the test suite

## Project Structure

```
code_parser/          # Core parsing library
scripts/             # Utility scripts
tests/               # Test suite
docs/                # Documentation
```

## Dependencies

- Python 3.7+
- `esprima-python`: JavaScript parsing
- `beautifulsoup4`: HTML parsing
- `networkx`: Graph processing
- `pyvis`: Interactive visualization

## License

This project is licensed under the MIT License - see the LICENSE file for details. 