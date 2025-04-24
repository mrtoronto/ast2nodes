#!/usr/bin/env python3
import os
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict, field

from code_parser.parsers.python_parser import parse_python_file
from code_parser.parsers.javascript_parser import parse_javascript_file
from code_parser.parsers.html_parser import parse_html_file
from code_parser.entities import Variable, ClassDef, FunctionDef, FunctionCall, FileEntity, FolderEntity

os.makedirs('data', exist_ok=True)

@dataclass
class MergedEntity:
    """Base class for merged entities that can come from multiple files"""
    name: str
    type: str  # 'variable', 'class', 'function', 'function_call'
    sources: List[Dict[str, Any]] = field(default_factory=list)  # List of source files and line numbers
    properties: Dict[str, Any] = field(default_factory=dict)  # Metadata properties from entities
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
    
    def _get_scoped_key(self, entity_type: str, name: str, source_file: str, 
                        class_name: Optional[str] = None, function_name: Optional[str] = None) -> str:
        """Helper to consistently generate scoped keys"""
        if class_name:
            if entity_type == 'function':
                return f"func:{class_name}.{name}"
            elif entity_type == 'variable':
                return f"var:{class_name}.{name}"
            elif entity_type == 'call':
                return f"call:{source_file}:{class_name}.{name}"
        elif function_name:
            if entity_type == 'variable':
                return f"var:{function_name}:{name}"
            elif entity_type == 'call':
                return f"call:{source_file}:{function_name}:{name}"
        
        # Module-level entities
        if entity_type == 'class':
            return f"class:{source_file}:{name}"
        elif entity_type == 'function':
            return f"func:{source_file}:{name}"
        elif entity_type == 'variable':
            return f"var:{source_file}:{name}"
        elif entity_type == 'call':
            return f"call:{source_file}:{name}"
        elif entity_type == 'file':
            # Use the full source_file path for file keys
            return f"file:{source_file}"
        elif entity_type == 'folder':
            # Use just the folder name for folder keys
            return f"folder:{name}"
        
        return f"{entity_type}:{name}"  # Fallback

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
            key = self._get_scoped_key(
                'variable', 
                entity.name, 
                source_file,
                class_name=entity.defined_in_class if hasattr(entity, 'defined_in_class') else None,
                function_name=entity.defined_in_function if hasattr(entity, 'defined_in_function') else None
            )
            if debug: print(f"Variable key: {key}")
            
        elif entity_class == 'ClassDef':
            entity_type = 'class'
            key = self._get_scoped_key('class', entity.name, source_file)
            if debug: print(f"Class key: {key}")
            
        elif entity_class == 'FunctionDef':
            entity_type = 'function'
            key = self._get_scoped_key(
                'function',
                entity.name,
                source_file,
                class_name=entity.parent_class if hasattr(entity, 'parent_class') else None
            )
            if debug: print(f"Function key: {key}")
            
        elif entity_class == 'FunctionCall':
            entity_type = 'function_call'
            key = self._get_scoped_key(
                'call',
                entity.name,
                source_file,
                class_name=entity.caller_class if hasattr(entity, 'caller_class') else None,
                function_name=entity.caller_function if hasattr(entity, 'caller_function') else None
            )
            if debug: print(f"Function call key: {key}")
            
        elif entity_class == 'FileEntity':
            entity_type = 'file'
            key = self._get_scoped_key('file', entity.name, source_file)
            if debug: print(f"File key: {key}")
            
        elif entity_class == 'FolderEntity':
            entity_type = 'folder'
            key = self._get_scoped_key('folder', entity.name, source_file)
            if debug: print(f"Folder key: {key}")
            
        else:
            if debug: print(f"Unknown entity type: {entity_class}")
            return  # Unknown entity type
        
        # Create or update entity
        if key not in self.entities:
            if debug: print(f"Creating new entity with key {key}")
            merged_entity = MergedEntity(
                name=entity.name,
                type=entity_type,
                sources=[source]
            )
            # Copy properties if they exist
            if hasattr(entity, 'properties'):
                merged_entity.properties.update(entity.properties)
            self.entities[key] = merged_entity
        else:
            if debug: print(f"Updating existing entity with key {key}")
            self.entities[key].sources.append(source)
            if hasattr(entity, 'properties'):
                self.entities[key].properties.update(entity.properties)

        # Add relationships based on entity class name
        if entity_class == 'Variable':
            # Variable is used by functions
            if hasattr(entity, 'used_in_functions'):
                for func_name in entity.used_in_functions:
                    func_key = self._get_scoped_key(
                        'function',
                        func_name,
                        source_file,
                        class_name=entity.defined_in_class if hasattr(entity, 'defined_in_class') else None
                    )
                    self.entities[key].relationships['used_by'].add(func_key)
                    if func_key in self.entities:
                        self.entities[func_key].relationships['uses'].add(key)
            
            # Variable is defined in a function/class
            if hasattr(entity, 'defined_in_function') and entity.defined_in_function:
                definer_key = self._get_scoped_key(
                    'function',
                    entity.defined_in_function,
                    source_file,
                    class_name=entity.defined_in_class if hasattr(entity, 'defined_in_class') else None
                )
                self.entities[key].relationships['defined_by'].add(definer_key)
                if definer_key in self.entities:
                    self.entities[definer_key].relationships['defines'].add(key)
            
            if hasattr(entity, 'defined_in_class') and entity.defined_in_class:
                class_key = self._get_scoped_key('class', entity.defined_in_class, source_file)
                self.entities[key].relationships['defined_by'].add(class_key)
                if class_key in self.entities:
                    self.entities[class_key].relationships['defines'].add(key)
                    
        elif entity_class == 'ClassDef':
            # Class defines methods and variables
            if hasattr(entity, 'methods'):
                for method_name in entity.methods:
                    method_key = self._get_scoped_key('function', method_name, source_file, class_name=entity.name)
                    self.entities[key].relationships['defines'].add(method_key)
            
            if hasattr(entity, 'instance_variables'):
                for var_name in entity.instance_variables:
                    var_key = self._get_scoped_key('variable', var_name, source_file, class_name=entity.name)
                    self.entities[key].relationships['defines'].add(var_key)
                
        elif entity_class == 'FunctionDef':
            # Function uses and defines variables
            if hasattr(entity, 'used_variables'):
                for var_name in entity.used_variables:
                    var_key = self._get_scoped_key(
                        'variable',
                        var_name,
                        source_file,
                        class_name=entity.parent_class if hasattr(entity, 'parent_class') else None
                    )
                    self.entities[key].relationships['uses'].add(var_key)
            
            if hasattr(entity, 'defined_variables'):
                for var_name in entity.defined_variables:
                    var_key = self._get_scoped_key(
                        'variable',
                        var_name,
                        source_file,
                        class_name=entity.parent_class if hasattr(entity, 'parent_class') else None
                    )
                    self.entities[key].relationships['defines'].add(var_key)
            
            # Function calls other functions
            if hasattr(entity, 'called_functions'):
                for func_name in entity.called_functions:
                    if '.' in func_name:
                        # If it's a method call, preserve the full path
                        call_key = f"func:{func_name}"
                    else:
                        # For regular functions, scope to the file
                        call_key = self._get_scoped_key('function', func_name, source_file)
                    self.entities[key].relationships['calls'].add(call_key)
                    if call_key in self.entities:
                        self.entities[call_key].relationships['called_by'].add(key)
                        
        elif entity_class == 'FunctionCall':
            # Track caller-callee relationship
            if hasattr(entity, 'caller_function') and entity.caller_function:
                caller_key = self._get_scoped_key(
                    'function',
                    entity.caller_function,
                    source_file,
                    class_name=entity.caller_class if hasattr(entity, 'caller_class') else None
                )
                self.entities[key].relationships['called_by'].add(caller_key)
                if caller_key in self.entities:
                    self.entities[caller_key].relationships['calls'].add(key)
            
            # For method calls on variables (like app.route), track the variable usage
            if '.' in entity.name:
                var_name = entity.name.split('.')[0]
                var_key = self._get_scoped_key('variable', var_name, source_file)
                self.entities[key].relationships['uses'].add(var_key)
                if var_key in self.entities:
                    self.entities[var_key].relationships['used_by'].add(key)
            
            # Track the function being called
            if '.' in entity.name:
                # If it's a method call, preserve the full path
                called_key = f"func:{entity.name}"
            else:
                # For regular functions, scope to the file
                called_key = self._get_scoped_key('function', entity.name, source_file)
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
                    'properties': entity.properties,
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
    
    # Get absolute and relative paths for root
    abs_directory = os.path.abspath(directory)
    root_name = os.path.basename(abs_directory)
    
    # Create root folder entity with absolute path
    root_folder = FolderEntity(
        name=root_name,
        line_number=0,
        column_offset=0,
        path='.',
        parent_folder=None
    )
    root_folder.sources = [{
        'file': '.',
        'parser': 'folder',
        'line_number': 0,
        'column_offset': 0
    }]
    graph.add_source('.', 'folder', [root_folder])
    
    # Track all files and folders for relationship building
    all_files = []
    folder_hierarchy = {}  # path -> parent_path
    top_level_items = set()  # Track items directly under root
    
    # First pass: collect all files and folders
    for root, dirs, files in os.walk(directory):
        # Skip virtual environment directories
        dirs[:] = [d for d in dirs if not is_venv_directory(os.path.join(root, d))]
        
        rel_path = os.path.relpath(root, directory)
        
        if rel_path == '.':
            # Add top-level directories to root's defines
            for d in dirs:
                if not is_venv_directory(os.path.join(root, d)):
                    top_level_items.add(f"folder:{d}")
            # Add top-level files to root's defines
            for f in files:
                if not is_venv_directory(os.path.join(root, f)) and (f.endswith('.py') or f.endswith('.js') or f.endswith('.html')):
                    top_level_items.add(f"file:{f}")
        else:
            parent_folder = os.path.dirname(rel_path) if rel_path != '.' else '.'
            current_folder = os.path.basename(rel_path)
            
            # If parent is root directory, use root_name
            if parent_folder == '.' or parent_folder == '':
                parent_folder = root_name
                top_level_items.add(f"folder:{current_folder}")
            
            folder_hierarchy[current_folder] = parent_folder
            
            folder_entity = FolderEntity(
                name=current_folder,
                line_number=0,
                column_offset=0,
                path=rel_path,
                parent_folder=parent_folder
            )
            folder_entity.sources = [{
                'file': rel_path,
                'parser': 'folder',
                'line_number': 0,
                'column_offset': 0
            }]
            graph.add_source(rel_path, 'folder', [folder_entity])
        
        # Track files
        for file in files:
            if is_venv_directory(os.path.join(root, file)):
                continue
            if not (file.endswith('.py') or file.endswith('.js') or file.endswith('.html')):
                continue
                
            file_path = os.path.join(root, file)
            rel_file_path = os.path.relpath(file_path, directory)
            parent_folder = os.path.basename(root) if rel_path != '.' else root_name
            all_files.append((rel_file_path, parent_folder))
            
            file_entity = FileEntity(
                name=file,
                line_number=0,
                column_offset=0,
                path=rel_file_path,
                parent_folder=parent_folder
            )
            file_entity.sources = [{
                'file': rel_file_path,
                'parser': 'file',
                'line_number': 0,
                'column_offset': 0
            }]
            graph.add_source(rel_file_path, 'file', [file_entity])
    
    # Add all top-level items to root folder's relationships
    root_key = f"folder:{root_name}"
    if root_key in graph.entities:
        graph.entities[root_key].relationships['defines'].update(top_level_items)
    
    # Second pass: establish folder hierarchy relationships
    for folder_name, parent_name in folder_hierarchy.items():
        folder_key = f"folder:{folder_name}"
        parent_key = f"folder:{parent_name}"
        
        # Parent folder defines child folder
        if parent_key in graph.entities:
            graph.entities[parent_key].relationships['defines'].add(folder_key)
        
        # Child folder is defined by parent folder
        if folder_key in graph.entities:
            graph.entities[folder_key].relationships['defined_by'].add(parent_key)
    
    # Third pass: establish folder-file relationships
    for rel_file_path, parent_folder in all_files:
        # Use the full relative path for the file key to maintain uniqueness
        file_key = f"file:{rel_file_path}"
        folder_key = f"folder:{parent_folder}"
        
        # Folder defines file
        if folder_key in graph.entities:
            graph.entities[folder_key].relationships['defines'].add(file_key)
        
        # File is defined by folder
        if file_key in graph.entities:
            graph.entities[file_key].relationships['defined_by'].add(folder_key)
            
        # Now parse the file contents
        try:
            file_path = os.path.join(directory, rel_file_path)
            print(f"\nParsing {file_path}")
            
            # Determine parser type based on file extension
            parser_type = None
            parser = None
            
            if rel_file_path.endswith('.py'):
                parser_type = 'python'
                parser = parse_python_file(file_path)
            elif rel_file_path.endswith('.js'):
                parser_type = 'javascript'
                parser = parse_javascript_file(file_path)
            elif rel_file_path.endswith('.html'):
                parser_type = 'html'
                parser = parse_html_file(file_path)
            
            if not parser:
                continue
            
            # Process classes
            if hasattr(parser, 'classes'):
                print(f"Found {len(parser.classes)} classes")
                for cls in parser.classes:
                    print(f"  Adding class: {cls.name}")
                    graph.add_source(rel_file_path, parser_type, [cls])
                    # Update file's defined entities
                    class_key = f"class:{rel_file_path}:{cls.name}"
                    if file_key in graph.entities:
                        graph.entities[file_key].relationships['defines'].add(class_key)
                    if class_key in graph.entities:
                        graph.entities[class_key].relationships['defined_by'].add(file_key)
            
            # Process functions
            if hasattr(parser, 'functions'):
                print(f"Found {len(parser.functions)} functions")
                for func in parser.functions:
                    print(f"  Adding function: {func.name}")
                    graph.add_source(rel_file_path, parser_type, [func])
                    # Update file's defined entities
                    func_key = f"func:{rel_file_path}:{func.name}"
                    if file_key in graph.entities:
                        graph.entities[file_key].relationships['defines'].add(func_key)
                    if func_key in graph.entities:
                        graph.entities[func_key].relationships['defined_by'].add(file_key)
            
            # Process variables
            if hasattr(parser, 'variables'):
                print(f"Found {len(parser.variables)} variables")
                for var in parser.variables:
                    print(f"  Adding variable: {var.name}")
                    graph.add_source(rel_file_path, parser_type, [var])
                    # Update file's defined entities
                    var_key = f"var:{rel_file_path}:{var.name}"
                    if file_key in graph.entities:
                        graph.entities[file_key].relationships['defines'].add(var_key)
                    if var_key in graph.entities:
                        graph.entities[var_key].relationships['defined_by'].add(file_key)
            
            # Process function calls
            if hasattr(parser, 'function_calls'):
                print(f"Found {len(parser.function_calls)} function calls")
                for call in parser.function_calls:
                    print(f"  Adding function call: {call.name}")
                    graph.add_source(rel_file_path, parser_type, [call])
                    # Update file's used entities
                    call_key = f"call:{rel_file_path}:{call.name}"
                    if file_key in graph.entities:
                        graph.entities[file_key].relationships['uses'].add(call_key)
                    if call_key in graph.entities:
                        graph.entities[call_key].relationships['used_by'].add(file_key)
                
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nTotal entities found: {len(graph.entities)}")
    print("Entity types:", set(e.type for e in graph.entities.values()))
    
    # Print relationship counts
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