"""
Tool definitions and handlers for the Code Knowledge Graph MCP Server
"""

import json
import sys
import traceback
import logging
from typing import List, Optional
import networkx as nx
from collections import defaultdict

import mcp.types as types
from mcp.models import (
    GraphQuery, CallerRequest
)
from mcp.graph_manager import GraphManager

logger = logging.getLogger("code_graph_mcp.tools")

def get_tool_definitions() -> list[types.Tool]:
    """Return the list of available tools"""
    return [
        types.Tool(
            name="ping",
            description="Simple test tool to verify server operation",
            inputSchema={
                "type": "object",
                "properties": {
                    "random_string": {
                        "type": "string",
                        "description": "Dummy parameter for no-parameter tools"
                    }
                }
            }
        ),
        types.Tool(
            name="search_code",
            description="Search for code entities matching specific criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["function", "variable", "class", "function_call"],
                        "description": "Type of entity to search for"
                    },
                    "name_pattern": {
                        "type": "string",
                        "description": "Pattern to match against entity names"
                    },
                    "relationship_type": {
                        "type": "string",
                        "enum": ["calls", "defines", "defined_by", "uses", "called_by", "used_by"],
                        "description": "Type of relationship to filter by"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path to filter entities by"
                    }
                }
            }
        ),
        types.Tool(
            name="get_entity_info",
            description="Get detailed information about a specific code entity",
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the entity to look up"
                    }
                }
            }
        ),
        types.Tool(
            name="find_dependencies",
            description="Find all dependencies for a given entity",
            inputSchema={
                "type": "object",
                "required": ["entity_name"],
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to find dependencies for"
                    },
                    "relationship_type": {
                        "type": "string",
                        "enum": ["calls", "defines", "defined_by", "uses", "called_by", "used_by"],
                        "description": "Type of relationship to filter by"
                    }
                }
            }
        ),
        types.Tool(
            name="find_callers",
            description="Find all functions that call the specified function",
            inputSchema={
                "type": "object",
                "required": ["function_name"],
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the function to find callers for"
                    }
                }
            }
        ),
        types.Tool(
            name="find_class_hierarchy",
            description="Get the inheritance hierarchy for a class",
            inputSchema={
                "type": "object",
                "required": ["class_name"],
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Name of the class to find hierarchy for"
                    }
                }
            }
        ),
        types.Tool(
            name="find_code_path",
            description="Find execution paths between two code entities",
            inputSchema={
                "type": "object",
                "required": ["source", "target"],
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source entity name"
                    },
                    "target": {
                        "type": "string",
                        "description": "Target entity name"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum path length to consider"
                    }
                }
            }
        ),
        types.Tool(
            name="find_usage_patterns",
            description="Find common patterns of how an entity is used across the codebase",
            inputSchema={
                "type": "object",
                "required": ["entity_name"],
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to analyze"
                    },
                    "pattern_type": {
                        "type": "string",
                        "enum": ["argument_patterns", "return_value_usage", "common_combinations"],
                        "description": "Type of usage pattern to analyze"
                    }
                }
            }
        ),
        types.Tool(
            name="analyze_impact",
            description="Analyze the potential impact of modifying an entity",
            inputSchema={
                "type": "object",
                "required": ["entity_name"],
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to analyze"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "How many levels of dependencies to analyze"
                    }
                }
            }
        ),
        types.Tool(
            name="find_similar_entities",
            description="Find entities with similar patterns or relationships",
            inputSchema={
                "type": "object",
                "required": ["entity_name"],
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity to find similarities for"
                    },
                    "similarity_type": {
                        "type": "string",
                        "enum": ["relationship_pattern", "usage_pattern", "structural"],
                        "description": "Type of similarity to look for"
                    }
                }
            }
        ),
        types.Tool(
            name="analyze_module_dependencies",
            description="Analyze dependencies at the module/file level",
            inputSchema={
                "type": "object",
                "required": ["module_path"],
                "properties": {
                    "module_path": {
                        "type": "string",
                        "description": "Path to the module to analyze"
                    },
                    "include_external": {
                        "type": "boolean",
                        "description": "Whether to include external dependencies"
                    }
                }
            }
        ),
        types.Tool(
            name="find_dead_code",
            description="Find potentially unused or dead code",
            inputSchema={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["function", "class", "module"],
                        "description": "Scope of analysis"
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "description": "Confidence threshold for considering code as dead"
                    }
                }
            }
        )
    ]

async def handle_tool_call(name: str, arguments: dict, graph: GraphManager) -> list[types.TextContent]:
    """Handle a tool call with the given name and arguments"""
    print(f"Tool called: {name} with arguments: {arguments}", file=sys.stderr)
    
    try:
        if name == "ping":
            return [types.TextContent(type="text", text="pong")]
            
        elif name == "search_code":
            query = GraphQuery(
                entity_type=arguments.get("entity_type"),
                name_pattern=arguments.get("name_pattern"),
                relationship_type=arguments.get("relationship_type"),
                file_path=arguments.get("file_path")
            )
            results = graph.search_entities(query)
            return [types.TextContent(type="text", text=json.dumps([r.dict() for r in results]))]
            
        elif name == "get_entity_info":
            result = graph.get_entity(arguments["name"])
            return [types.TextContent(type="text", text=json.dumps(result.dict() if result else None))]
            
        elif name == "find_dependencies":
            deps = graph.get_dependencies(
                arguments["entity_name"],
                arguments.get("relationship_type")
            )
            return [types.TextContent(type="text", text=json.dumps([d.dict() for d in deps]))]
            
        elif name == "find_callers":
            callers = graph.find_callers(CallerRequest(function_name=arguments["function_name"]))
            return [types.TextContent(type="text", text=json.dumps([c.dict() for c in callers]))]
            
        elif name == "find_class_hierarchy":
            entity = graph.get_entity(arguments["class_name"])
            if not entity or entity.type != "class":
                hierarchy = {"parents": [], "children": []}
            else:
                hierarchy = {
                    "parents": entity.relationships.get("defined_by", []),
                    "children": entity.relationships.get("defines", [])
                }
            return [types.TextContent(type="text", text=json.dumps(hierarchy))]
            
        elif name == "find_code_path":
            source = graph.get_entity(arguments["source"])
            target = graph.get_entity(arguments["target"])
            max_depth = arguments.get("max_depth", 5)
            
            if not source or not target:
                return [types.TextContent(type="text", text=json.dumps({"paths": []}))]
                
            # Build a directed graph from the relationships
            G = nx.DiGraph()
            for entity_name, entity_data in graph.graph.items():
                for rel_type, targets in entity_data.get('relationships', {}).items():
                    for target_name in targets:
                        G.add_edge(entity_name, target_name, relationship=rel_type)
            
            try:
                paths = list(nx.all_simple_paths(G, source.name, target.name, cutoff=max_depth))
                path_details = []
                for path in paths:
                    edges = []
                    for i in range(len(path)-1):
                        edges.append({
                            "from": path[i],
                            "to": path[i+1],
                            "relationship": G[path[i]][path[i+1]]["relationship"]
                        })
                    path_details.append({"nodes": path, "edges": edges})
                return [types.TextContent(type="text", text=json.dumps({"paths": path_details}))]
            except nx.NetworkXNoPath:
                return [types.TextContent(type="text", text=json.dumps({"paths": []}))]
                
        elif name == "find_usage_patterns":
            entity = graph.get_entity(arguments["entity_name"])
            pattern_type = arguments.get("pattern_type", "argument_patterns")
            
            if not entity:
                return [types.TextContent(type="text", text=json.dumps({"patterns": []}))]
                
            patterns = defaultdict(int)
            
            # Analyze based on pattern type
            if pattern_type == "argument_patterns":
                # Find all calls to this entity and analyze argument patterns
                for caller_name, caller_data in graph.graph.items():
                    if "calls" in caller_data.get('relationships', {}):
                        if entity.name in caller_data['relationships']['calls']:
                            # Here we would analyze the actual call pattern
                            # For now just count the calls
                            patterns["direct_call"] += 1
                            
            elif pattern_type == "return_value_usage":
                # Find where the return value is used
                for user_name, user_data in graph.graph.items():
                    if "uses" in user_data.get('relationships', {}):
                        if entity.name in user_data['relationships']['uses']:
                            patterns["return_value_used"] += 1
                            
            elif pattern_type == "common_combinations":
                # Find what other entities are commonly used alongside this one
                for other_name, other_data in graph.graph.items():
                    if other_name != entity.name:
                        common_users = set()
                        for user_name, user_data in graph.graph.items():
                            if "uses" in user_data.get('relationships', {}):
                                if entity.name in user_data['relationships']['uses'] and \
                                   other_name in user_data['relationships']['uses']:
                                    common_users.add(user_name)
                        if common_users:
                            patterns[f"used_with_{other_name}"] = len(common_users)
                            
            return [types.TextContent(type="text", text=json.dumps({"patterns": dict(patterns)}))]
            
        elif name == "analyze_impact":
            entity = graph.get_entity(arguments["entity_name"])
            depth = arguments.get("depth", 2)
            
            if not entity:
                return [types.TextContent(type="text", text=json.dumps({"impact": {}}))]
                
            impact = {
                "direct_dependencies": [],
                "indirect_dependencies": [],
                "potential_impact_score": 0
            }
            
            # Build dependency graph
            G = nx.DiGraph()
            for entity_name, entity_data in graph.graph.items():
                for rel_type, targets in entity_data.get('relationships', {}).items():
                    for target_name in targets:
                        G.add_edge(entity_name, target_name, relationship=rel_type)
            
            # Find all descendants up to specified depth
            for d in range(1, depth + 1):
                descendants = set()
                for node in G.nodes():
                    try:
                        paths = nx.all_simple_paths(G, entity.name, node, cutoff=d)
                        for path in paths:
                            if len(path) == d + 1:  # path length is number of nodes
                                descendants.add(node)
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue
                
                if d == 1:
                    impact["direct_dependencies"] = list(descendants)
                else:
                    impact["indirect_dependencies"].extend(list(descendants))
            
            # Calculate impact score based on number and depth of dependencies
            impact["potential_impact_score"] = len(impact["direct_dependencies"]) + \
                                             len(impact["indirect_dependencies"]) * 0.5
            
            return [types.TextContent(type="text", text=json.dumps({"impact": impact}))]
            
        elif name == "find_similar_entities":
            entity = graph.get_entity(arguments["entity_name"])
            similarity_type = arguments.get("similarity_type", "relationship_pattern")
            
            if similarity_type not in ["relationship_pattern", "usage_pattern", "structural"]:
                raise ValueError(f"Invalid similarity type: {similarity_type}")
            
            if not entity:
                return [types.TextContent(type="text", text=json.dumps({"similar_entities": []}))]
                
            similar_entities = []
            
            for other_name, other_data in graph.graph.items():
                if other_name == entity.name:
                    continue
                    
                similarity_score = 0
                
                if similarity_type == "relationship_pattern":
                    # Compare relationship patterns
                    entity_rels = entity.relationships
                    other_rels = other_data.get('relationships', {})
                    
                    # Calculate Jaccard similarity of relationships
                    for rel_type in set(entity_rels.keys()) | set(other_rels.keys()):
                        entity_targets = set(entity_rels.get(rel_type, []))
                        other_targets = set(other_rels.get(rel_type, []))
                        if entity_targets or other_targets:
                            similarity_score += len(entity_targets & other_targets) / \
                                             len(entity_targets | other_targets)
                            
                elif similarity_type == "usage_pattern":
                    # Compare how they are used by other entities
                    entity_users = set()
                    other_users = set()
                    
                    for user_name, user_data in graph.graph.items():
                        for rel_type, targets in user_data.get('relationships', {}).items():
                            if entity.name in targets:
                                entity_users.add(user_name)
                            if other_name in targets:
                                other_users.add(user_name)
                    
                    if entity_users or other_users:
                        similarity_score = len(entity_users & other_users) / \
                                        len(entity_users | other_users)
                            
                elif similarity_type == "structural":
                    # Compare structural properties (type, number of relationships, etc)
                    if entity.type == other_data.get('type'):
                        similarity_score += 0.5
                        
                    # Compare number of relationships
                    entity_rel_count = sum(len(targets) for targets in entity.relationships.values())
                    other_rel_count = sum(len(targets) for targets in other_data.get('relationships', {}).values())
                    
                    if max(entity_rel_count, other_rel_count) > 0:
                        similarity_score += 0.5 * (1 - abs(entity_rel_count - other_rel_count) / \
                                                 max(entity_rel_count, other_rel_count))
                
                if similarity_score > 0.3:  # Threshold for similarity
                    similar_entities.append({
                        "name": other_name,
                        "similarity_score": similarity_score,
                        "type": other_data.get('type')
                    })
            
            # Sort by similarity score
            similar_entities.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return [types.TextContent(type="text", text=json.dumps({"similar_entities": similar_entities[:10]}))]
            
        elif name == "analyze_module_dependencies":
            module_path = arguments["module_path"]
            include_external = arguments.get("include_external", False)
            
            module_entities = []
            module_deps = {
                "internal": defaultdict(list),
                "external": defaultdict(list)
            }
            
            # Find all entities in the module
            for entity_name, entity_data in graph.graph.items():
                for source in entity_data.get('sources', []):
                    if source.get('file') == module_path:
                        module_entities.append(entity_name)
                        break
            
            # Analyze their dependencies
            for entity_name in module_entities:
                entity = graph.get_entity(entity_name)
                if not entity:
                    continue
                    
                for rel_type, targets in entity.relationships.items():
                    for target_name in targets:
                        target = graph.get_entity(target_name)
                        if not target:
                            continue
                            
                        # Check if target is in same module
                        target_in_module = False
                        for source in target.sources:
                            if source.get('file') == module_path:
                                target_in_module = True
                                break
                                
                        if target_in_module:
                            module_deps["internal"][rel_type].append({
                                "from": entity_name,
                                "to": target_name
                            })
                        elif include_external:
                            module_deps["external"][rel_type].append({
                                "from": entity_name,
                                "to": target_name
                            })
            
            return [types.TextContent(type="text", text=json.dumps({
                "module_path": module_path,
                "entity_count": len(module_entities),
                "dependencies": module_deps
            }))]
            
        elif name == "find_dead_code":
            scope = arguments.get("scope", "function")
            confidence_threshold = arguments.get("confidence_threshold", 0.8)
            
            dead_code = []
            
            for entity_name, entity_data in graph.graph.items():
                if entity_data.get('type') != scope:
                    continue
                    
                # Calculate usage score
                usage_score = 0
                total_weight = 0
                
                # Check if entity is used by others
                used_by_count = 0
                for other_name, other_data in graph.graph.items():
                    for rel_type, targets in other_data.get('relationships', {}).items():
                        if entity_name in targets:
                            used_by_count += 1
                
                if used_by_count == 0:
                    usage_score = 0
                    total_weight = 1
                else:
                    usage_score += 1
                    total_weight += 1
                
                # Check if entity uses others (dead code might not have dependencies)
                if not entity_data.get('relationships'):
                    usage_score += 0
                    total_weight += 0.5
                else:
                    usage_score += 0.5
                    total_weight += 0.5
                
                # Calculate final confidence
                confidence = 1 - (usage_score / total_weight if total_weight > 0 else 0)
                
                if confidence >= confidence_threshold:
                    dead_code.append({
                        "name": entity_name,
                        "type": entity_data.get('type'),
                        "confidence": confidence,
                        "used_by_count": used_by_count
                    })
            
            return [types.TextContent(type="text", text=json.dumps({"dead_code": dead_code}))]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        traceback.print_exc(file=sys.stderr)
        raise 