# AST2Nodes

A tool for building and analyzing knowledge graphs from your codebase. Extract relationships between code entities, understand dependencies, and gain insights through intelligent code analysis by converting Abstract Syntax Trees (ASTs) to knowledge graph nodes.

## Overview

AST2Nodes analyzes your codebase to build a comprehensive graph of code relationships. It supports multiple languages (Python, JavaScript, HTML, CSS) and provides intelligent analysis through MCP (Machine Comprehension Protocol) integration.

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
cd ast2nodes

# Install dependencies
pip install -r requirements.txt
```

2. Generate a knowledge graph from your codebase:
```