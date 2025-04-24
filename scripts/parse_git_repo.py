#!/usr/bin/env python3
import os
import shutil
import tempfile
import argparse
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from scripts.parse_local_files import parse_directory, CodebaseGraph
from code_parser.parsers.python_parser import parse_python_file
from code_parser.parsers.javascript_parser import parse_javascript_file
from code_parser.parsers.html_parser import parse_html_file
from code_parser.entities import FileEntity, FolderEntity

class GitRepoGraph(CodebaseGraph):
    """Extension of CodebaseGraph that handles git repository paths"""
    
    def __init__(self, base_dir: str):
        super().__init__()
        self.base_dir = os.path.abspath(base_dir)
    
    def _make_path_relative(self, path: str) -> str:
        """Convert an absolute path to be relative to base_dir"""
        if os.path.isabs(path):
            try:
                return os.path.relpath(path, self.base_dir)
            except ValueError:
                # If paths are on different drives, just return the original path
                return path
        return path
    
    def add_source(self, source_file: str, parser_type: str, entities: list):
        # Convert absolute path to relative path
        rel_path = self._make_path_relative(source_file)
        
        # Update source paths in entities to be relative
        for entity in entities:
            if hasattr(entity, 'sources'):
                if entity.sources is None:
                    entity.sources = []
                for source in entity.sources:
                    if 'file' in source:
                        source['file'] = self._make_path_relative(source['file'])
            if hasattr(entity, 'path'):
                entity.path = self._make_path_relative(entity.path)
            if hasattr(entity, 'parent_folder'):
                if entity.parent_folder:
                    entity.parent_folder = self._make_path_relative(entity.parent_folder)
        
        super().add_source(rel_path, parser_type, entities)

def is_valid_git_url(url: str) -> bool:
    """Check if a URL appears to be a valid git repository URL."""
    parsed = urlparse(url)
    return (
        parsed.scheme in ('http', 'https', 'git') and
        'github.com' in parsed.netloc  # For now, we only support GitHub
    )

def get_repo_name(url: str) -> str:
    """Extract repository name from git URL."""
    # Handle both HTTPS and SSH URLs
    if url.endswith('.git'):
        url = url[:-4]
    return url.split('/')[-1]

def clone_repository(url: str, target_dir: str) -> bool:
    """Clone a git repository to the target directory."""
    import subprocess
    
    try:
        subprocess.run(['git', 'clone', url, target_dir], 
                      check=True,
                      capture_output=True,
                      text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e.stderr}")
        return False

def parse_git_repository(repo_url: str, output_file: Optional[str] = None) -> bool:
    """
    Parse a git repository and generate a code knowledge graph.
    
    Args:
        repo_url: URL of the git repository
        output_file: Optional name for the output file. If not provided,
                    will use the repository name.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_valid_git_url(repo_url):
        print(f"Invalid git URL: {repo_url}")
        return False

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # Clone the repository
        if not clone_repository(repo_url, temp_dir):
            return False
            
        # Generate output filename if not provided
        if output_file is None:
            repo_name = get_repo_name(repo_url)
            output_file = f"{repo_name}_code_graph.json"
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs('data', exist_ok=True)
            
            # Initialize graph with base directory
            graph = GitRepoGraph(temp_dir)
            
            # Walk through the directory and parse files
            for root, dirs, files in os.walk(temp_dir):
                # Skip virtual environment directories
                dirs[:] = [d for d in dirs if not is_venv_directory(os.path.join(root, d))]
                
                # Add folder entity
                rel_path = os.path.relpath(root, temp_dir)
                if rel_path != '.':
                    parent_folder = os.path.dirname(rel_path)
                    folder_entity = FolderEntity(
                        name=os.path.basename(root),
                        line_number=0,
                        column_offset=0,
                        path=rel_path,
                        parent_folder=parent_folder if parent_folder != '.' else None
                    )
                    # Create source with relative path
                    folder_entity.sources = [{
                        'file': rel_path,
                        'parser': 'folder',
                        'line_number': 0,
                        'column_offset': 0
                    }]
                    graph.add_source(rel_path, 'folder', [folder_entity])
                    
                    # Update parent folder's subfolders list
                    if parent_folder != '.':
                        parent_key = f"folder:{parent_folder}"
                        if parent_key in graph.entities:
                            graph.entities[parent_key].relationships['defines'].add(f"folder:{rel_path}")
                
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_file_path = os.path.relpath(file_path, temp_dir)
                    
                    # Skip virtual environment files and non-source files
                    if is_venv_directory(file_path) or not (file.endswith('.py') or file.endswith('.js') or file.endswith('.html')):
                        continue
                        
                    print(f"\nParsing {os.path.relpath(file_path, temp_dir)}")
                    
                    try:
                        # Create file entity
                        file_entity = FileEntity(
                            name=file,
                            line_number=0,
                            column_offset=0,
                            path=rel_file_path,
                            parent_folder=rel_path if rel_path != '.' else None
                        )
                        # Create source with relative path
                        file_entity.sources = [{
                            'file': rel_file_path,
                            'parser': 'file',
                            'line_number': 0,
                            'column_offset': 0
                        }]
                        graph.add_source(rel_file_path, 'file', [file_entity])
                        
                        # Update parent folder's files list
                        if rel_path != '.':
                            folder_key = f"folder:{rel_path}"
                            if folder_key in graph.entities:
                                graph.entities[folder_key].relationships['defines'].add(f"file:{rel_file_path}")
                        
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
                        
                        # Add entities to graph
                        if hasattr(parser, 'classes'):
                            for cls in parser.classes:
                                graph.add_source(file_path, parser_type, [cls])
                                # Update file's defined entities
                                file_key = f"file:{rel_file_path}"
                                class_key = f"class:{rel_file_path}:{cls.name}"
                                if file_key in graph.entities:
                                    graph.entities[file_key].relationships['defines'].add(class_key)
                        
                        if hasattr(parser, 'functions'):
                            for func in parser.functions:
                                graph.add_source(file_path, parser_type, [func])
                                # Update file's defined entities
                                file_key = f"file:{rel_file_path}"
                                func_key = f"func:{rel_file_path}:{func.name}"
                                if file_key in graph.entities:
                                    graph.entities[file_key].relationships['defines'].add(func_key)
                        
                        if hasattr(parser, 'variables'):
                            for var in parser.variables:
                                graph.add_source(file_path, parser_type, [var])
                                # Update file's defined entities
                                file_key = f"file:{rel_file_path}"
                                var_key = f"var:{rel_file_path}:{var.name}"
                                if file_key in graph.entities:
                                    graph.entities[file_key].relationships['defines'].add(var_key)
                        
                        if hasattr(parser, 'function_calls'):
                            for call in parser.function_calls:
                                graph.add_source(file_path, parser_type, [call])
                                # Update file's used entities
                                file_key = f"file:{rel_file_path}"
                                call_key = f"call:{rel_file_path}:{call.name}"
                                if file_key in graph.entities:
                                    graph.entities[file_key].relationships['uses'].add(call_key)
                                
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")
                        import traceback
                        traceback.print_exc()
            
            # Save the graph
            graph.save_to_file('data/' + output_file)
            print(f"\nSuccessfully generated code graph at: data/{output_file}")
            return True
            
        except Exception as e:
            print(f"Error parsing repository: {e}")
            return False

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

def main():
    parser = argparse.ArgumentParser(description='Parse a git repository and create a relationship graph')
    parser.add_argument('repo_url', help='URL of the git repository')
    parser.add_argument('--output', '-o', help='Output JSON file name')
    
    args = parser.parse_args()
    parse_git_repository(args.repo_url, args.output)

if __name__ == '__main__':
    main() 