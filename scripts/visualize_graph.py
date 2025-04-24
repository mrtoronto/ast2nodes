#!/usr/bin/env python3
import json
import argparse
import networkx as nx
from pyvis.network import Network
from typing import Dict, Any, Set
from collections import defaultdict
import os

os.makedirs('data', exist_ok=True)

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

def load_graph(input_file: str) -> Dict[str, Any]:
    """Load the graph from a JSON file"""
    with open(input_file, 'r') as f:
        data = json.load(f)
        
    # Filter out entities from venv directories
    filtered_entities = {}
    for key, entity in data['entities'].items():
        # Check if any of the entity's sources are from venv
        if not any(is_venv_directory(s['file']) for s in entity['sources']):
            filtered_entities[key] = entity
    
    data['entities'] = filtered_entities
    return data

def get_node_size(entity: Dict[str, Any], base_size: int = 20) -> int:
    """Calculate node size based on number of relationships"""
    total_relationships = sum(len(rels) for rels in entity['relationships'].values())
    # Logarithmic scaling to prevent huge nodes
    return base_size + min(30, total_relationships * 2)

def create_network_graph(data: Dict[str, Any], 
                       entity_types: Set[str] = None,
                       relationship_types: Set[str] = None,
                       max_nodes: int = 100) -> Network:
    """Create a network visualization from the graph data"""
    # Initialize network with physics enabled and HTML support
    net = Network(height="750px", width="100%", notebook=False, bgcolor="#ffffff", font_color="#333333")
    net.toggle_physics(True)
    
    # Set up node colors by type with better contrast
    colors = {
        'variable': '#2ecc71',    # Green
        'class': '#e74c3c',       # Red
        'function': '#3498db',    # Blue
        'function_call': '#9b59b6', # Purple
        'file': '#f1c40f',       # Yellow
        'folder': '#e67e22'      # Orange
    }
    
    # Group numbers for each type
    groups = {
        'variable': 1,
        'class': 2,
        'function': 3,
        'function_call': 4,
        'file': 5,
        'folder': 6
    }
    
    # Create networkx graph
    G = nx.DiGraph()  # Using DiGraph for directed edges
    
    # First pass: Build folder path mappings and hierarchy
    folder_paths = {}  # Map folder keys to their full paths
    folder_keys = {}   # Map full paths to folder keys
    folder_hierarchy = {}  # Keep track of parent-child folder relationships
    
    # First, collect all folder paths and keys
    for key, entity in data['entities'].items():
        if entity['type'] == 'folder':
            # Get all possible paths for this folder
            paths = set()
            for source in entity['sources']:
                if source['file'] != '.':
                    paths.add(source['file'])
            if not paths:  # If no valid paths found, use the name
                paths.add(entity['name'])
            
            # Store all paths for this folder key
            folder_paths[key] = paths
            # Map each path back to the folder key
            for path in paths:
                folder_keys[path] = key
                folder_keys[f"folder:{path}"] = key  # Also store with "folder:" prefix
                # Store partial paths
                parts = path.split('/')
                for i in range(len(parts)):
                    partial = '/'.join(parts[:i+1])
                    if partial not in folder_keys:
                        folder_keys[partial] = key
                    if f"folder:{partial}" not in folder_keys:
                        folder_keys[f"folder:{partial}"] = key
    
    # Now build hierarchy based on paths
    for key, paths in folder_paths.items():
        for path in paths:
            path_parts = path.split('/')
            if len(path_parts) > 1:
                parent_path = '/'.join(path_parts[:-1])
                if parent_path in folder_keys:
                    folder_hierarchy[key] = folder_keys[parent_path]
    
    # Count relationships for node sizing
    relationship_counts = defaultdict(int)
    for key, entity in data['entities'].items():
        for rel_type, targets in entity['relationships'].items():
            relationship_counts[key] += len(targets)
            # Map any full path references to their actual keys
            for target in targets:
                if target in folder_keys:
                    relationship_counts[folder_keys[target]] += 1
    
    # Add nodes
    node_count = 0
    for key, entity in data['entities'].items():
        # Skip if we're filtering by entity type and type doesn't match
        if entity_types and entity['type'] not in entity_types:
            continue
            
        # Create tooltip content
        tooltip_parts = []
        tooltip_parts.append(f"{entity['type'].title()}: {entity['name']}")
        if entity['type'] == 'folder':
            paths = folder_paths.get(key, {entity['name']})
            tooltip_parts.append(f"Paths: {', '.join(paths)}")
        tooltip_parts.append("\nSources:")
        for source in entity['sources']:
            tooltip_parts.append(f"File: {source['file']}, Line: {source['line_number']}")
        tooltip_parts.append("\nRelationships:")
        for rel_type, targets in entity['relationships'].items():
            if targets:
                tooltip_parts.append(f"{rel_type}: {len(targets)}")
        tooltip = "\n".join(tooltip_parts)
        
        # Add node
        G.add_node(key, 
                  title=tooltip,
                  color=colors.get(entity['type'], '#95a5a6'),
                  size=get_node_size(entity),
                  label=entity['name'],
                  group=groups.get(entity['type'], 0))
        node_count += 1
        
        if node_count >= max_nodes:
            break
    
    # Add edges from explicit relationships and folder hierarchy
    added_edges = set()  # Keep track of edges we've added
    for key, entity in data['entities'].items():
        if key not in G:
            continue
            
        # Add explicit relationships
        for rel_type, targets in entity['relationships'].items():
            if relationship_types and rel_type not in relationship_types:
                continue
                
            for target in targets:
                # Map the target to its actual key if it's a full path reference
                actual_target = folder_keys.get(target, target)
                if actual_target in G and (key, actual_target) not in added_edges:
                    edge_tooltip = (
                        f"Relationship: {rel_type}\n"
                        f"From: {entity['name']}\n"
                        f"To: {data['entities'][actual_target]['name'] if actual_target in data['entities'] else actual_target}"
                    )
                    
                    edge_color = '#666666'
                    edge_width = 1.5
                    if entity['type'] == 'folder' and data['entities'].get(actual_target, {}).get('type') == 'folder':
                        edge_color = '#e67e22'
                        edge_width = 2.5
                    
                    G.add_edge(key, actual_target, 
                             title=edge_tooltip,
                             label=rel_type,
                             arrows='to',
                             width=edge_width,
                             color={'color': edge_color, 'opacity': 0.8})
                    added_edges.add((key, actual_target))
        
        # Add implicit folder hierarchy relationships
        if key in folder_hierarchy and folder_hierarchy[key] in G and (folder_hierarchy[key], key) not in added_edges:
            parent_key = folder_hierarchy[key]
            edge_tooltip = (
                f"Relationship: parent_folder\n"
                f"From: {data['entities'][parent_key]['name']}\n"
                f"To: {entity['name']}\n"
                f"Paths: {', '.join(folder_paths[key])}"
            )
            G.add_edge(parent_key, key,
                      title=edge_tooltip,
                      label="contains",
                      arrows='to',
                      width=2.5,
                      color={'color': '#e67e22', 'opacity': 0.8})
            added_edges.add((parent_key, key))
    
    # Convert networkx graph to pyvis
    net.from_nx(G)
    
    # Configure options for better visualization
    net.set_options("""
    {
      "nodes": {
        "font": {
          "size": 12,
          "face": "Arial"
        },
        "tooltipDelay": 200
      },
      "edges": {
        "font": {
          "size": 10,
          "face": "Arial"
        },
        "color": {
          "inherit": false
        },
        "smooth": {
          "type": "continuous",
          "forceDirection": "none"
        }
      },
      "physics": {
        "hierarchicalRepulsion": {
          "centralGravity": 0.0,
          "springLength": 200,
          "springConstant": 0.01,
          "nodeDistance": 150,
          "damping": 0.09
        },
        "maxVelocity": 50,
        "minVelocity": 0.1,
        "solver": "hierarchicalRepulsion",
        "timestep": 0.5,
        "stabilization": {
          "iterations": 1000
        }
      },
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "nodeSpacing": 150,
          "treeSpacing": 200
        }
      },
      "interaction": {
        "navigationButtons": true,
        "keyboard": true,
        "hover": true,
        "multiselect": true,
        "tooltipDelay": 200
      },
      "groups": {
        "1": {"color": {"background": "#2ecc71", "border": "#27ae60"}},
        "2": {"color": {"background": "#e74c3c", "border": "#c0392b"}},
        "3": {"color": {"background": "#3498db", "border": "#2980b9"}},
        "4": {"color": {"background": "#9b59b6", "border": "#8e44ad"}},
        "5": {"color": {"background": "#f1c40f", "border": "#f39c12"}},
        "6": {"color": {"background": "#e67e22", "border": "#d35400"}}
      }
    }
    """)
    
    # Add a simple HTML legend
    legend_html = """
    <div style="position: absolute; top: 10px; right: 10px; padding: 10px; background-color: white; border: 1px solid #ccc; border-radius: 5px;">
        <h3 style="margin-top: 0;">Legend</h3>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #2ecc71; margin-right: 5px;"></span>Variable</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #e74c3c; margin-right: 5px;"></span>Class</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #3498db; margin-right: 5px;"></span>Function</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #9b59b6; margin-right: 5px;"></span>Function Call</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #f1c40f; margin-right: 5px;"></span>File</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #e67e22; margin-right: 5px;"></span>Folder</div>
    </div>
    """
    
    # Add a search box
    search_html = """
    <div style="position: absolute; top: 10px; left: 10px; padding: 10px; background-color: white; border: 1px solid #ccc; border-radius: 5px;">
        <input type="text" id="nodeSearch" placeholder="Search nodes..." style="padding: 5px;">
        <button onclick="searchNodes()" style="padding: 5px;">Search</button>
    </div>
    <script>
    function searchNodes() {
        var searchText = document.getElementById('nodeSearch').value.toLowerCase();
        var nodes = network.body.data.nodes.get();
        var matchingNodes = nodes.filter(node => 
            node.label.toLowerCase().includes(searchText) ||
            node.title.toLowerCase().includes(searchText)
        );
        
        // Reset all nodes
        nodes.forEach(node => {
            network.body.data.nodes.update({id: node.id, color: node.color});
        });
        
        // Highlight matching nodes
        if (matchingNodes.length > 0) {
            matchingNodes.forEach(node => {
                network.body.data.nodes.update({
                    id: node.id,
                    color: '#ffff00'  // Highlight in yellow
                });
            });
            
            // Focus on the first matching node
            network.focus(matchingNodes[0].id, {
                scale: 1.2,
                animation: true
            });
        }
    }
    </script>
    """
    
    # Add custom HTML
    net.html += legend_html + search_html
    
    return net

def get_visualization_filename(input_file: str) -> str:
    """Generate visualization filename based on input filename"""
    # Get the base name without extension
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    # Remove _code_graph suffix if present
    if base_name.endswith('_code_graph'):
        base_name = base_name[:-11]
    return f"{base_name}_visualization.html"

def main():
    parser = argparse.ArgumentParser(description='Visualize a code relationship graph')
    parser.add_argument('input', help='Input JSON file containing the graph')
    parser.add_argument('--output', '-o', 
                       help='Output HTML file for visualization (defaults to input_name_visualization.html)')
    parser.add_argument('--entity-types', '-e', nargs='+',
                       choices=['variable', 'class', 'function', 'function_call', 'file', 'folder'],
                       help='Filter by entity types')
    parser.add_argument('--relationship-types', '-r', nargs='+',
                       choices=['defines', 'uses', 'calls', 'defined_by', 'used_by', 'called_by'],
                       help='Filter by relationship types')
    parser.add_argument('--max-nodes', '-m', type=int, default=100,
                       help='Maximum number of nodes to display')
    
    args = parser.parse_args()
    
    # Generate output filename if not provided
    if not args.output:
        args.output = get_visualization_filename(args.input)
    
    # Load the graph
    print(f"Loading graph from {args.input}")
    data = load_graph(args.input)
    
    # If no entity types specified, include all types
    if not args.entity_types:
        args.entity_types = ['variable', 'class', 'function', 'function_call', 'file', 'folder']
    
    # Create the visualization
    print("Creating visualization...")
    net = create_network_graph(
        data,
        entity_types=set(args.entity_types),
        relationship_types=set(args.relationship_types) if args.relationship_types else None,
        max_nodes=args.max_nodes
    )
    
    # Save the visualization
    output_path = 'data/' + args.output
    print(f"Saving visualization to {output_path}")
    net.save_graph(output_path)
    print(f"Done! Open {output_path} in your web browser to view the visualization.")

if __name__ == '__main__':
    main() 