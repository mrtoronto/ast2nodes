#!/usr/bin/env python3
import os
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict, field

from code_parser.parsers.python_parser import parse_python_file
from code_parser.parsers.javascript_parser import parse_javascript_file
from code_parser.parsers.html_parser import parse_html_file
from code_parser.entities import Variable, ClassDef, FunctionDef, FunctionCall

os.makedirs('data', exist_ok=True)

@dataclass
class MergedEntity:
    """Base class for merged entities that can come from multiple files"""
    name: str
    type: str  # 'variable', 'class', 'function', 'function_call'
    sources: List[Dict[str, Any]] = field(default_factory=list)  # List of source files and line numbers
    relationships: Dict[str, Set[str]] = field(default_factory=lambda: {
        'defines': set(),  # Things this entity defines
        'uses': set(),     # Things this entity uses
        'calls': set(),    # Functions this entity calls
        'defined_by': set(), # Things that define this entity
        'used_by': set(),   # Things that use this entity
        'called_by': set()  # Functions that call this entity
    })

class CodebaseGraph:
    """Represents a graph of code entities and their relationships"""
    
    def __init__(self):
        self.entities: Dict[str, MergedEntity] = {}
        
    def add_source(self, source_file: str, parser_type: str, entities: List[Any]):
        """Add entities from a source file to the graph"""
        for entity in entities:
            self._merge_entity(entity, source_file, parser_type)
    
    def _merge_entity(self, entity: Any, source_file: str, parser_type: str):
        """Merge an entity into the graph, creating or updating as needed"""
        # Create a source record
        source = {
            'file': source_file,
            'parser': parser_type,
            'line_number': entity.line_number,
            'column_offset': entity.column_offset
        }
        
        # Debug output for first 5 entities only
        debug = len(self.entities) < 5
        if debug:
            print(f"\nProcessing entity: {entity}")
        
        # Determine entity type and create key
        entity_type = None
        key = None
        
        # Check entity type by class name instead of isinstance
        entity_class = entity.__class__.__name__
        
        if entity_class == 'Variable':
            entity_type = 'variable'
            key = f"var:{entity.name}"
            if hasattr(entity, 'defined_in_class') and entity.defined_in_class:
                key = f"var:{entity.defined_in_class}.{entity.name}"
            elif hasattr(entity, 'defined_in_function') and entity.defined_in_function:
                key = f"var:{entity.defined_in_function}:{entity.name}"
            if debug: print(f"Variable key: {key}")
        elif entity_class == 'ClassDef':
            entity_type = 'class'
            key = f"class:{entity.name}"
            if debug: print(f"Class key: {key}")
        elif entity_class == 'FunctionDef':
            entity_type = 'function'
            key = f"func:{entity.name}"
            if hasattr(entity, 'parent_class') and entity.parent_class:
                key = f"func:{entity.parent_class}.{entity.name}"
            if debug: print(f"Function key: {key}")
        elif entity_class == 'FunctionCall':
            entity_type = 'function_call'
            key = f"call:{entity.name}"
            if hasattr(entity, 'caller_class') and entity.caller_class:
                key = f"call:{entity.caller_class}.{entity.name}"
            elif hasattr(entity, 'caller_function') and entity.caller_function:
                key = f"call:{entity.caller_function}:{entity.name}"
            if debug: print(f"Function call key: {key}")
        else:
            if debug: print(f"Unknown entity type: {entity_class}")
            return  # Unknown entity type
        
        # Create or update entity
        if key not in self.entities:
            if debug: print(f"Creating new entity with key {key}")
            self.entities[key] = MergedEntity(
                name=entity.name,
                type=entity_type,
                sources=[source]
            )
        else:
            if debug: print(f"Updating existing entity with key {key}")
            self.entities[key].sources.append(source)
        
        # Add relationships based on entity class name
        if entity_class == 'Variable':
            # Variable is used by functions
            if hasattr(entity, 'used_in_functions'):
                for func_name in entity.used_in_functions:
                    func_key = f"func:{func_name}"
                    if hasattr(entity, 'defined_in_class') and entity.defined_in_class:
                        func_key = f"func:{entity.defined_in_class}.{func_name}"
                    self.entities[key].relationships['used_by'].add(func_key)
                    if func_key in self.entities:
                        self.entities[func_key].relationships['uses'].add(key)
            
            # Variable is defined in a function/class
            if hasattr(entity, 'defined_in_function') and entity.defined_in_function:
                definer_key = f"func:{entity.defined_in_function}"
                if hasattr(entity, 'defined_in_class') and entity.defined_in_class:
                    definer_key = f"func:{entity.defined_in_class}.{entity.defined_in_function}"
                self.entities[key].relationships['defined_by'].add(definer_key)
                if definer_key in self.entities:
                    self.entities[definer_key].relationships['defines'].add(key)
            
            if hasattr(entity, 'defined_in_class') and entity.defined_in_class:
                class_key = f"class:{entity.defined_in_class}"
                self.entities[key].relationships['defined_by'].add(class_key)
                if class_key in self.entities:
                    self.entities[class_key].relationships['defines'].add(key)
                    
        elif entity_class == 'ClassDef':
            # Class defines methods and variables
            if hasattr(entity, 'methods'):
                for method_name in entity.methods:
                    method_key = f"func:{entity.name}.{method_name}"
                    self.entities[key].relationships['defines'].add(method_key)
            
            if hasattr(entity, 'instance_variables'):
                for var_name in entity.instance_variables:
                    var_key = f"var:{entity.name}.{var_name}"
                    self.entities[key].relationships['defines'].add(var_key)
                
        elif entity_class == 'FunctionDef':
            # Function uses and defines variables
            if hasattr(entity, 'used_variables'):
                for var_name in entity.used_variables:
                    var_key = f"var:{var_name}"
                    if hasattr(entity, 'parent_class') and entity.parent_class:
                        var_key = f"var:{entity.parent_class}.{var_name}"
                    self.entities[key].relationships['uses'].add(var_key)
            
            if hasattr(entity, 'defined_variables'):
                for var_name in entity.defined_variables:
                    var_key = f"var:{var_name}"
                    if hasattr(entity, 'parent_class') and entity.parent_class:
                        var_key = f"var:{entity.parent_class}.{var_name}"
                    self.entities[key].relationships['defines'].add(var_key)
            
            # Function calls other functions
            if hasattr(entity, 'called_functions'):
                for func_name in entity.called_functions:
                    call_key = f"func:{func_name}"
                    self.entities[key].relationships['calls'].add(call_key)
                    if call_key in self.entities:
                        self.entities[call_key].relationships['called_by'].add(key)
            
            # Function belongs to class
            if hasattr(entity, 'parent_class') and entity.parent_class:
                class_key = f"class:{entity.parent_class}"
                self.entities[key].relationships['defined_by'].add(class_key)
                
        elif entity_class == 'FunctionCall':
            # Track caller-callee relationship
            if hasattr(entity, 'caller_function') and entity.caller_function:
                caller_key = f"func:{entity.caller_function}"
                if hasattr(entity, 'caller_class') and entity.caller_class:
                    caller_key = f"func:{entity.caller_class}.{entity.caller_function}"
                self.entities[key].relationships['called_by'].add(caller_key)
                if caller_key in self.entities:
                    self.entities[caller_key].relationships['calls'].add(key)
            
            # Track the function being called
            called_key = f"func:{entity.name}"
            self.entities[key].relationships['calls'].add(called_key)
            if called_key in self.entities:
                self.entities[called_key].relationships['called_by'].add(key)
    
    def save_to_file(self, output_file: str):
        """Save the graph to a JSON file"""
        # Convert sets to lists for JSON serialization
        output_data = {
            'entities': {
                key: {
                    'name': entity.name,
                    'type': entity.type,
                    'sources': entity.sources,
                    'relationships': {
                        rel_type: list(rel_set)
                        for rel_type, rel_set in entity.relationships.items()
                    }
                }
                for key, entity in self.entities.items()
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

def is_venv_directory(path: str) -> bool:
    """Check if a path is or is within a virtual environment directory"""
    venv_indicators = {
        'venv',
        'virtualenv',
        '.venv',
        'env',
        '.env',
        '.tox',
        '.nox',
        'site-packages',
        'dist-packages',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ipynb_checkpoints'
    }
    
    # Check if any part of the path matches a venv indicator
    path_parts = path.split(os.sep)
    return any(part in venv_indicators for part in path_parts)

def parse_directory(directory: str, output_file: str):
    """Parse all supported files in a directory and create a merged graph"""
    graph = CodebaseGraph()
    
    # First pass: collect all entities
    for root, dirs, files in os.walk(directory):
        # Skip virtual environment directories
        dirs[:] = [d for d in dirs if not is_venv_directory(os.path.join(root, d))]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip virtual environment files and non-source files
            if is_venv_directory(file_path) or not (file.endswith('.py') or file.endswith('.js') or file.endswith('.html')):
                continue
                
            print(f"\nParsing {file_path}")
            
            try:
                # Determine parser type based on file extension
                parser_type = None
                parser = None
                
                if file.endswith('.py'):
                    parser_type = 'python'
                    parser = parse_python_file(file_path)
                elif file.endswith('.js'):
                    parser_type = 'javascript'
                    parser = parse_javascript_file(file_path)
                elif file.endswith('.html'):
                    parser_type = 'html'
                    parser = parse_html_file(file_path)
                
                if not parser:
                    continue
                
                # First add classes since they can contain methods and variables
                if hasattr(parser, 'classes'):
                    print(f"Found {len(parser.classes)} classes")
                    for cls in parser.classes:
                        print(f"  Adding class: {cls.name}")
                        graph.add_source(file_path, parser_type, [cls])
                
                # Then add functions which can reference classes
                if hasattr(parser, 'functions'):
                    print(f"Found {len(parser.functions)} functions")
                    for func in parser.functions:
                        print(f"  Adding function: {func.name}")
                        graph.add_source(file_path, parser_type, [func])
                
                # Then add variables which may reference both classes and functions
                if hasattr(parser, 'variables'):
                    print(f"Found {len(parser.variables)} variables")
                    for var in parser.variables:
                        print(f"  Adding variable: {var.name}")
                        graph.add_source(file_path, parser_type, [var])
                
                # Finally add function calls which may reference all of the above
                if hasattr(parser, 'function_calls'):
                    print(f"Found {len(parser.function_calls)} function calls")
                    for call in parser.function_calls:
                        print(f"  Adding function call: {call.name}")
                        graph.add_source(file_path, parser_type, [call])
                    
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                import traceback
                traceback.print_exc()
    
    # Second pass: ensure all relationships are bidirectional
    for key, entity in graph.entities.items():
        # For each relationship type that should have a corresponding inverse
        relationship_pairs = [
            ('defines', 'defined_by'),
            ('uses', 'used_by'),
            ('calls', 'called_by')
        ]
        
        for rel_type, inverse_type in relationship_pairs:
            for target_key in entity.relationships[rel_type]:
                if target_key in graph.entities:
                    # Add the inverse relationship
                    graph.entities[target_key].relationships[inverse_type].add(key)
    
    print(f"\nTotal entities found: {len(graph.entities)}")
    print("Entity types:", set(e.type for e in graph.entities.values()))
    
    # Print some stats about relationships
    relationship_counts = {
        'defines': 0,
        'uses': 0,
        'calls': 0,
        'defined_by': 0,
        'used_by': 0,
        'called_by': 0
    }
    
    for entity in graph.entities.values():
        for rel_type, rel_set in entity.relationships.items():
            relationship_counts[rel_type] += len(rel_set)
    
    print("\nRelationship counts:")
    for rel_type, count in relationship_counts.items():
        print(f"  {rel_type}: {count}")
    
    # Save the graph
    graph.save_to_file('data/' + output_file)
    print(f"Saved code graph to {output_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse a directory of code files and create a relationship graph')
    parser.add_argument('directory', help='Directory to parse')
    parser.add_argument('--output', '-o', default='code_graph.json', help='Output JSON file')
    
    args = parser.parse_args()
    parse_directory(args.directory, args.output)

if __name__ == '__main__':
    main() 