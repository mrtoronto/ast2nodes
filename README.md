# Code Parser

A Python library for parsing and analyzing Python, JavaScript, HTML, and CSS code. The library extracts various code entities like variables, functions, classes, event listeners, HTML elements, CSS rules, and more, making it easy to understand and analyze code structure. It also provides tools for generating and visualizing code relationship graphs.

## Features

- Python code parsing:
  - Variable declarations and assignments
  - Function definitions with arguments and return types
  - Class definitions with methods and docstrings
  - Function calls with arguments and keywords

- JavaScript code parsing:
  - Variable declarations (const, let, var)
  - Function declarations and arrow functions
  - Class definitions with methods and constructors
  - Event listener registration and handling

- HTML code parsing:
  - Complete DOM tree structure with nested elements
  - Element attributes and content
  - Script tag analysis (both inline and external)
  - Style tag and CSS link parsing
  - Form elements and input fields
  - Line number tracking for all elements
  - Query elements by tag name, class, or ID

- CSS code parsing:
  - Rule extraction with selectors and properties
  - Media query parsing and analysis
  - Line number tracking for all rules
  - Search rules by selector or property
  - Support for complex selectors and pseudo-classes

- Code Relationship Graph Generation:
  - Extract relationships between code entities
  - Track variable usage and definitions
  - Map function calls and dependencies
  - Identify class hierarchies and relationships
  - Generate JSON representation of code graph
  - Automatic virtual environment exclusion

- Interactive Graph Visualization:
  - Interactive force-directed graph layout
  - Color-coded nodes by entity type
  - Relationship arrows with labels
  - Search functionality with highlighting
  - Node sizing based on relationships
  - Detailed tooltips with source information
  - Interactive legend and filtering options

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/code-parser.git
cd code-parser

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Python Code Analysis

```python
from code_parser import parse_python_file

# Parse a Python file
parser = parse_python_file('path/to/your/file.py')

# Access extracted entities
print("Variables:", parser.variables)
print("Functions:", parser.functions)
print("Classes:", parser.classes)
print("Function Calls:", parser.function_calls)
```

### JavaScript Code Analysis

```python
from code_parser import parse_javascript_file

# Parse a JavaScript file
parser = parse_javascript_file('path/to/your/file.js')

# Access extracted entities
print("Variables:", parser.variables)
print("Functions:", parser.functions)
print("Classes:", parser.classes)
print("Event Listeners:", parser.event_listeners)
```

### HTML Code Analysis

```python
from code_parser import HTMLParser

# Parse an HTML file
parser = HTMLParser('path/to/your/file.html')

# Query elements
divs = parser.get_elements_by_tag('div')
containers = parser.get_elements_by_class('container')
main_content = parser.get_elements_by_id('main-content')[0]

# Access scripts and styles
for script in parser.scripts:
    print(f"Script at line {script.line_number}")
    if script.src:
        print(f"External script: {script.src}")
    else:
        print(f"Inline script content: {script.content}")
```

### Generate Code Relationship Graph

```bash
# Generate a graph for a directory
python scripts/parse_local_files.py /path/to/your/codebase --output code_graph.json

# The script will:
# - Parse all Python, JavaScript, and HTML files
# - Extract code entities and their relationships
# - Automatically exclude virtual environment directories
# - Save the graph in JSON format
```

### Visualize Code Relationships

```bash
# Create an interactive visualization
python scripts/visualize_graph.py code_graph.json

# Options:
# Filter by entity types
python scripts/visualize_graph.py code_graph.json -e class function

# Filter by relationship types
python scripts/visualize_graph.py code_graph.json -r defines uses calls

# Limit number of nodes
python scripts/visualize_graph.py code_graph.json -m 50

# Custom output file
python scripts/visualize_graph.py code_graph.json -o my_visualization.html
```

The visualization provides:
- Interactive graph with physics simulation
- Color-coded nodes by entity type:
  - Variables: Green
  - Classes: Red
  - Functions: Blue
  - Function Calls: Purple
- Node size reflects number of relationships
- Hover tooltips showing entity details and source locations
- Search functionality with node highlighting
- Edge labels showing relationship types
- Zoom, pan, and drag controls
- Interactive legend

## Project Structure

```
code_parser/
├── __init__.py           # Package initialization
├── entities.py           # Data classes for code entities
├── parsers/             # Parser implementations
│   ├── __init__.py
│   ├── python_parser.py  # Python code parser
│   ├── javascript_parser.py  # JavaScript code parser
│   ├── html_parser.py    # HTML code parser
│   └── css_parser.py     # CSS code parser
scripts/
├── parse_local_files.py  # Graph generation script
└── visualize_graph.py    # Graph visualization script
tests/
├── test_code_parser.py   # Python parser tests
├── test_javascript_parser.py  # JavaScript parser tests
├── test_html_parser.py   # HTML parser tests
└── test_css_parser.py    # CSS parser tests
```

## Dependencies

- Python 3.7+
- `esprima-python`: JavaScript parsing
- `ast` module (built-in): Python parsing
- `beautifulsoup4`: HTML parsing
- `networkx`: Graph processing
- `pyvis`: Interactive visualization

## License

This project is licensed under the MIT License - see the LICENSE file for details. 