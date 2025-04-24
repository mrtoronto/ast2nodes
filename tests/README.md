# Testing Documentation

This directory contains the comprehensive test suite for the code parser and knowledge graph tools.

## Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_python_parser.py   # Python parser tests
pytest tests/test_javascript_parser.py   # JavaScript parser tests
pytest tests/test_html_parser.py   # HTML parser tests
pytest tests/test_css_parser.py   # CSS parser tests
pytest tests/test_graph_tools.py   # Graph tools tests
```

## Test Coverage

### Python Parser Tests (5 tests)
- Variable declaration and assignment tracking
- Function definition analysis with arguments and return types
- Class hierarchy and inheritance relationships
- Function call detection with argument analysis
- Module-level imports and dependencies

### JavaScript Parser Tests (4 tests)
- Variable declarations (const, let, var)
- Function declarations and arrow functions
- Class definitions with methods and constructors
- Event listener registration and handling

### HTML Parser Tests (6 tests)
- DOM tree structure and nesting
- Element attributes and content extraction
- Script tag analysis (inline and external)
- Style tag and CSS link parsing
- Form elements and input field detection
- Element querying by tag, class, and ID

### CSS Parser Tests (5 tests)
- Rule extraction and selector parsing
- Property and value validation
- Media query analysis
- Complex selector handling
- Pseudo-class and pseudo-element support

### Graph Tools Tests (7 tests)
- Entity relationship mapping
- Dependency tracking and analysis
- Code path identification
- Call hierarchy construction
- Impact analysis accuracy
- Dead code detection
- Module dependency resolution

## Adding New Tests

When adding new tests:
1. Follow the existing test file naming convention: `test_<component>.py`
2. Group related test cases using test classes
3. Use descriptive test names that indicate the functionality being tested
4. Include both positive and negative test cases
5. Add appropriate test data in the `test_data` directory if needed

## Test Data

The `test_data` directory contains sample code files used for testing:
- Python files with various language features
- JavaScript files with different coding patterns
- HTML files with diverse structures
- CSS files with different rule types
- Complex codebases for graph analysis testing 