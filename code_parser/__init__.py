"""Code parser package for analyzing Python, JavaScript, HTML, and CSS code"""

from code_parser.entities import (
    Variable, ClassDef, FunctionDef, FunctionCall,
    JSVariable, JSFunction, JSClass, JSEventListener
)
from code_parser.parsers.python_parser import parse_python_file
from code_parser.parsers.javascript_parser import parse_javascript_file
from code_parser.parsers.html_parser import HTMLParser
from code_parser.parsers.css_parser import CSSParser

__all__ = [
    'Variable', 'ClassDef', 'FunctionDef', 'FunctionCall',
    'JSVariable', 'JSFunction', 'JSClass', 'JSEventListener',
    'parse_python_file', 'parse_javascript_file', 'HTMLParser',
    'CSSParser'
] 