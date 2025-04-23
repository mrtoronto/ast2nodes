"""
Graph Manager for Code Knowledge Graph
Handles loading and querying the code knowledge graph
"""

import json
import sys
import traceback
from typing import List, Dict, Optional

from mcp.models import (
    EntityTypeStr, RelationTypeStr, CodeEntity, GraphQuery,
    DependencyInfo, CallerRequest
)

class GraphManager:
    def __init__(self, graph_file: str):
        print(f"Loading graph from {graph_file}", file=sys.stderr)
        try:
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
                if not isinstance(graph_data, dict):
                    raise ValueError(f"Expected graph data to be a dictionary, got {type(graph_data)}")
                
                # The graph file has an outer 'entities' key
                if 'entities' not in graph_data:
                    print("Warning: No 'entities' key found in graph data", file=sys.stderr)
                    self.graph = {}
                else:
                    self.graph = graph_data['entities']
                    print(f"Graph loaded successfully with {len(self.graph)} entities", file=sys.stderr)
                    # Print first few entity types to help debug
                    sample_entities = list(self.graph.items())[:3]
                    for name, entity in sample_entities:
                        print(f"Sample entity - {name}: type={entity.get('type')}", file=sys.stderr)
                        
        except FileNotFoundError:
            print(f"Graph file not found: {graph_file}", file=sys.stderr)
            self.graph = {}
        except json.JSONDecodeError as e:
            print(f"Error parsing graph file: {e}", file=sys.stderr)
            self.graph = {}
        except Exception as e:
            print(f"Unexpected error loading graph: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            self.graph = {}

    def get_entity(self, name: str) -> Optional[CodeEntity]:
        """Get an entity by name"""
        print(f"Looking up entity: {name}", file=sys.stderr)
        
        # Try exact match first
        if name in self.graph:
            print(f"Found exact match for {name}", file=sys.stderr)
            entity = self.graph[name]
            return CodeEntity(
                name=name,
                type=entity['type'],
                sources=entity.get('sources', []),
                relationships=entity.get('relationships', {})
            )
        
        # Try with type prefixes
        prefixes = ['class:', 'function:', 'variable:', 'function_call:']
        for prefix in prefixes:
            prefixed_name = f"{prefix}{name}"
            if prefixed_name in self.graph:
                print(f"Found match with prefix: {prefixed_name}", file=sys.stderr)
                entity = self.graph[prefixed_name]
                return CodeEntity(
                    name=name,
                    type=entity['type'],
                    sources=entity.get('sources', []),
                    relationships=entity.get('relationships', {})
                )
        
        # Try finding by matching the part after any prefix
        for key, entity in self.graph.items():
            unprefixed = key.split(":")[-1] if ":" in key else key
            if unprefixed == name:
                print(f"Found match by unprefixed name: {key}", file=sys.stderr)
                return CodeEntity(
                    name=name,
                    type=entity['type'],
                    sources=entity.get('sources', []),
                    relationships=entity.get('relationships', {})
                )
        
        print(f"No match found for {name}", file=sys.stderr)
        return None

    def search_entities(self, query: GraphQuery) -> List[CodeEntity]:
        """Search for entities matching the query"""
        results = []
        for key, entity in self.graph.items():
            # Extract the unprefixed name
            name = key.split(":")[-1] if ":" in key else key
            
            if query.entity_type and entity['type'] != query.entity_type:
                continue
            if query.name_pattern and query.name_pattern.lower() not in name.lower():
                continue
            if query.file_path and entity.get('sources'):
                # Check if any source matches the file path
                if not any(source.get('file') == query.file_path for source in entity['sources']):
                    continue
            if query.relationship_type:
                if not entity.get('relationships') or query.relationship_type not in entity['relationships']:
                    continue
            
            results.append(CodeEntity(
                name=name,
                type=entity['type'],
                sources=entity.get('sources', []),
                relationships=entity.get('relationships', {})
            ))
        
        print(f"Search found {len(results)} results", file=sys.stderr)
        return results

    def get_dependencies(self, entity_name: str, relationship_type: Optional[RelationTypeStr] = None) -> List[DependencyInfo]:
        """Get dependencies for an entity"""
        entity = self.get_entity(entity_name)
        if not entity:
            return []
        
        dependencies = []
        for rel_type, targets in entity.relationships.items():
            if relationship_type and rel_type != relationship_type:
                continue
            for target in targets:
                target_entity = self.get_entity(target)
                if target_entity:
                    dependencies.append(DependencyInfo(
                        source=entity_name,
                        target=target,
                        relationship_type=rel_type,
                        source_type=entity.type,
                        target_type=target_entity.type
                    ))
        return dependencies

    def find_callers(self, request: CallerRequest) -> List[CodeEntity]:
        """Find all functions that call the specified function"""
        print(f"Finding callers for function: {request.function_name}", file=sys.stderr)
        
        # First get the target function to ensure it exists and get its full name
        target_func = self.get_entity(request.function_name)
        if not target_func:
            print(f"Target function {request.function_name} not found", file=sys.stderr)
            return []
            
        if target_func.type not in ['function', 'function_call']:
            print(f"Entity {request.function_name} is not a function", file=sys.stderr)
            return []
            
        # Search for entities that have a 'calls' relationship to our target
        callers = []
        for key, entity in self.graph.items():
            relationships = entity.get('relationships', {})
            calls = relationships.get('calls', [])
            
            # Check if this entity calls our target function
            if target_func.name in calls:
                caller_entity = self.get_entity(key.split(':')[-1])  # Get unprefixed name
                if caller_entity:
                    callers.append(caller_entity)
                    
        print(f"Found {len(callers)} callers for {request.function_name}", file=sys.stderr)
        return callers 