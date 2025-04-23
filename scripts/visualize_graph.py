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
    # Initialize network with physics enabled
    net = Network(height="750px", width="100%", notebook=False, bgcolor="#ffffff", font_color="#333333")
    net.toggle_physics(True)
    
    # Set up node colors by type with better contrast
    colors = {
        'variable': '#2ecc71',    # Green
        'class': '#e74c3c',       # Red
        'function': '#3498db',    # Blue
        'function_call': '#9b59b6' # Purple
    }
    
    # Group numbers for each type
    groups = {
        'variable': 1,
        'class': 2,
        'function': 3,
        'function_call': 4
    }
    
    # Create networkx graph
    G = nx.DiGraph()  # Using DiGraph for directed edges
    
    # Count relationships for node sizing
    relationship_counts = defaultdict(int)
    for key, entity in data['entities'].items():
        for rel_list in entity['relationships'].values():
            relationship_counts[key] += len(rel_list)
    
    # Add nodes
    node_count = 0
    for key, entity in data['entities'].items():
        # Skip if we're filtering by entity type
        if entity_types and entity['type'] not in entity_types:
            continue
            
        # Create detailed tooltip with source information
        sources = [f"File: {s['file']}, Line: {s['line_number']}" for s in entity['sources']]
        tooltip = f"<b>{entity['type'].title()}: {entity['name']}</b><br>"
        tooltip += f"Sources:<br>" + "<br>".join(sources)
        
        # Add node with enhanced properties
        G.add_node(key, 
                  title=tooltip,
                  color=colors.get(entity['type'], '#gray'),
                  size=get_node_size(entity),
                  label=entity['name'],
                  group=groups.get(entity['type'], 0))
        node_count += 1
        
        # Break if we've reached max nodes
        if node_count >= max_nodes:
            break
    
    # Add edges
    added_edges = set()
    for key, entity in data['entities'].items():
        if key not in G:
            continue
            
        for rel_type, targets in entity['relationships'].items():
            # Skip if we're filtering by relationship type
            if relationship_types and rel_type not in relationship_types:
                continue
                
            for target in targets:
                if target in G and (key, target) not in added_edges:
                    # Add directed edge with arrow
                    G.add_edge(key, target, 
                             title=rel_type,
                             label=rel_type,
                             arrows='to',
                             color={'color': '#666666', 'opacity': 0.8})
                    added_edges.add((key, target))
    
    # Convert networkx graph to pyvis
    net.from_nx(G)
    
    # Add a simple HTML legend
    legend_html = """
    <div style="position: absolute; top: 10px; right: 10px; padding: 10px; background-color: white; border: 1px solid #ccc; border-radius: 5px;">
        <h3 style="margin-top: 0;">Legend</h3>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #2ecc71; margin-right: 5px;"></span>Variable</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #e74c3c; margin-right: 5px;"></span>Class</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #3498db; margin-right: 5px;"></span>Function</div>
        <div><span style="display: inline-block; width: 20px; height: 20px; background-color: #9b59b6; margin-right: 5px;"></span>Function Call</div>
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
    
    # Configure physics and interaction
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 200,
          "springConstant": 0.08,
          "damping": 0.4
        },
        "maxVelocity": 50,
        "minVelocity": 0.1,
        "solver": "forceAtlas2Based",
        "timestep": 0.3
      },
      "interaction": {
        "navigationButtons": true,
        "keyboard": true,
        "hover": true,
        "multiselect": true
      },
      "edges": {
        "smooth": {
          "type": "continuous",
          "forceDirection": "none"
        },
        "color": {
          "inherit": false
        },
        "width": 1.5
      },
      "groups": {
        "1": {"color": {"background": "#2ecc71", "border": "#27ae60"}},
        "2": {"color": {"background": "#e74c3c", "border": "#c0392b"}},
        "3": {"color": {"background": "#3498db", "border": "#2980b9"}},
        "4": {"color": {"background": "#9b59b6", "border": "#8e44ad"}}
      }
    }
    """)
    
    # Add custom HTML
    net.html += legend_html + search_html
    
    return net

def main():
    parser = argparse.ArgumentParser(description='Visualize a code relationship graph')
    parser.add_argument('input', help='Input JSON file containing the graph')
    parser.add_argument('--output', '-o', default='graph_visualization.html', 
                       help='Output HTML file for visualization')
    parser.add_argument('--entity-types', '-e', nargs='+',
                       choices=['variable', 'class', 'function', 'function_call'],
                       help='Filter by entity types')
    parser.add_argument('--relationship-types', '-r', nargs='+',
                       choices=['defines', 'uses', 'calls', 'defined_by', 'used_by', 'called_by'],
                       help='Filter by relationship types')
    parser.add_argument('--max-nodes', '-m', type=int, default=100,
                       help='Maximum number of nodes to display')
    
    args = parser.parse_args()
    
    # Load the graph
    print(f"Loading graph from {args.input}")
    data = load_graph(args.input)
    
    # Create the visualization
    print("Creating visualization...")
    net = create_network_graph(
        data,
        entity_types=set(args.entity_types) if args.entity_types else None,
        relationship_types=set(args.relationship_types) if args.relationship_types else None,
        max_nodes=args.max_nodes
    )
    
    # Save the visualization
    print(f"Saving visualization to {args.output}")
    net.save_graph('data/' + args.output)
    print(f"Done! Open {args.output} in your web browser to view the visualization.")

if __name__ == '__main__':
    main() 