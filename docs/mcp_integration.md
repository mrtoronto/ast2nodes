# MCP Integration Guide

This guide explains how to integrate the code knowledge graph into your project using MCP (Machine Comprehension Protocol).

## Overview

The code knowledge graph provides intelligent code analysis capabilities through MCP, enabling:
- Semantic code search
- Entity relationship analysis
- Dependency tracking
- Call hierarchy analysis
- Impact analysis for code changes
- Dead code detection
- Module dependency analysis

## Setup

1. Generate the MCP configuration:
```bash
# Generate and save the configuration
./scripts/generate_mcp_config.py /path/to/your/graph.json -o .cursor/mcp.json

# Or print configuration to stdout
./scripts/generate_mcp_config.py /path/to/your/graph.json
```

2. Place the generated `mcp.json` in your project's `.cursor` directory.

## Available Tools

The MCP server provides several tools for code analysis:

### Code Search
- Search for specific code entities (functions, classes, variables)
- Filter by entity type, name pattern, or file path
- Find relationships between entities

### Dependency Analysis
- Track function calls and dependencies
- Analyze class hierarchies
- Find callers of specific functions
- Identify module-level dependencies

### Impact Analysis
- Analyze potential impact of code changes
- Find dead or unused code
- Detect common usage patterns
- Identify similar code structures

### Code Path Analysis
- Find execution paths between code entities
- Analyze control flow
- Track data flow between components

## Configuration Options

The `mcp.json` configuration supports:
- Custom graph file location
- Python interpreter selection
- Server startup arguments
- Tool-specific settings

## Best Practices

1. Keep your knowledge graph up to date:
   - Regenerate after significant code changes
   - Include all relevant code files
   - Exclude test and generated files

2. Optimize search performance:
   - Use specific entity types when searching
   - Provide file paths when known
   - Filter by relationship types

3. Handle large codebases:
   - Split analysis into modules
   - Use targeted searches
   - Filter visualization output

## Troubleshooting

Common issues and solutions:
1. Server not starting:
   - Check Python interpreter path
   - Verify graph file exists and is valid
   - Check file permissions

2. Search not finding results:
   - Verify entity names and types
   - Check file paths are correct
   - Regenerate graph if outdated

3. Performance issues:
   - Reduce search scope
   - Filter by specific types
   - Split large graphs into modules 