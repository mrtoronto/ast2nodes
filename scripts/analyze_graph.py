#!/usr/bin/env python3
"""
Graph Analysis Script

Analyzes the structure and contents of the code knowledge graph JSON file.
Provides insights about:
- Overall structure and nesting
- Types of entities and their frequencies
- Types of relationships and their frequencies
- Common patterns and statistics
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import pprint
import os

os.makedirs("data", exist_ok=True)

class GraphAnalyzer:
    def __init__(self, graph_data: Dict):
        self.graph_data = graph_data
        self.entity_types: Counter = Counter()
        self.relationship_types: Counter = Counter()
        self.field_names: Set[str] = set()
        self.max_depth = 0
        self.entity_count = 0
        self.relationship_count = 0

    def analyze_structure(self, obj: Any, depth: int = 0, path: str = "") -> None:
        """Recursively analyze the structure of the graph data"""
        self.max_depth = max(self.max_depth, depth)

        if isinstance(obj, dict):
            for key, value in obj.items():
                self.field_names.add(key)
                new_path = f"{path}.{key}" if path else key
                self.analyze_structure(value, depth + 1, new_path)
                
                # Try to identify entity types and relationships
                if isinstance(value, dict):
                    if "type" in value:
                        self.entity_types[value["type"]] += 1
                        self.entity_count += 1
                    if "relationships" in value:
                        self.analyze_relationships(value["relationships"])

        elif isinstance(obj, list):
            for item in obj:
                self.analyze_structure(item, depth + 1, path)

    def analyze_relationships(self, relationships: Dict) -> None:
        """Analyze relationship types and their frequencies"""
        for rel_type, targets in relationships.items():
            self.relationship_types[rel_type] += len(targets)
            self.relationship_count += len(targets)

    def get_summary(self) -> Dict:
        """Generate a summary of the analysis"""
        return {
            "structure": {
                "max_depth": self.max_depth,
                "field_names": sorted(list(self.field_names)),
                "total_entities": self.entity_count,
                "total_relationships": self.relationship_count
            },
            "entity_types": dict(self.entity_types.most_common()),
            "relationship_types": dict(self.relationship_types.most_common())
        }

def analyze_graph(graph_path: str) -> None:
    """Main function to analyze the graph file"""
    print(f"Analyzing graph file: {graph_path}")
    
    try:
        with open(graph_path, 'r') as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find graph file at {graph_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in graph file")
        return

    analyzer = GraphAnalyzer(graph_data)
    analyzer.analyze_structure(graph_data)
    summary = analyzer.get_summary()

    print("\n=== Graph Analysis Summary ===\n")
    print("Structure:")
    print(f"- Maximum nesting depth: {summary['structure']['max_depth']}")
    print(f"- Total entities: {summary['structure']['total_entities']}")
    print(f"- Total relationships: {summary['structure']['total_relationships']}")
    print("\nField names found:")
    for field in summary['structure']['field_names']:
        print(f"- {field}")

    print("\nEntity Types:")
    for etype, count in summary['entity_types'].items():
        print(f"- {etype}: {count}")

    print("\nRelationship Types:")
    for rtype, count in summary['relationship_types'].items():
        print(f"- {rtype}: {count}")

    # Save the detailed analysis to a file
    output_path = "data/graph_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nDetailed analysis saved to: {output_path}")

if __name__ == "__main__":
    graph_path = "graph.json"  # Default path
    analyze_graph(graph_path) 