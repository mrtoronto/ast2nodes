import json
import os
import pytest
from mcp.graph_manager import GraphManager
from mcp.tools import handle_tool_call

# Load test graph data
TEST_GRAPH_PATH = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'graph.json')

@pytest.fixture
def graph_manager():
    return GraphManager(TEST_GRAPH_PATH)

async def test_find_code_path(graph_manager):
    """Test finding code paths between entities"""
    result = await handle_tool_call(
        "find_code_path",
        {
            "source": "class:GraphManager",
            "target": "func:GraphManager.get_entity",
            "max_depth": 3
        },
        graph_manager
    )
    
    paths = json.loads(result[0].text)["paths"]
    assert len(paths) > 0
    # Check path structure
    path = paths[0]
    assert "nodes" in path
    assert "edges" in path
    assert len(path["nodes"]) >= 2
    assert len(path["edges"]) == len(path["nodes"]) - 1

async def test_find_usage_patterns(graph_manager):
    """Test finding usage patterns for an entity"""
    # Test argument patterns
    result = await handle_tool_call(
        "find_usage_patterns",
        {
            "entity_name": "func:GraphManager.get_entity",
            "pattern_type": "argument_patterns"
        },
        graph_manager
    )
    patterns = json.loads(result[0].text)["patterns"]
    assert isinstance(patterns, dict)
    
    # Test return value usage
    result = await handle_tool_call(
        "find_usage_patterns",
        {
            "entity_name": "func:GraphManager.get_entity",
            "pattern_type": "return_value_usage"
        },
        graph_manager
    )
    patterns = json.loads(result[0].text)["patterns"]
    assert isinstance(patterns, dict)
    
    # Test common combinations
    result = await handle_tool_call(
        "find_usage_patterns",
        {
            "entity_name": "func:GraphManager.get_entity",
            "pattern_type": "common_combinations"
        },
        graph_manager
    )
    patterns = json.loads(result[0].text)["patterns"]
    assert isinstance(patterns, dict)

async def test_analyze_impact(graph_manager):
    """Test analyzing impact of modifying an entity"""
    result = await handle_tool_call(
        "analyze_impact",
        {
            "entity_name": "class:GraphManager",
            "depth": 2
        },
        graph_manager
    )
    
    impact = json.loads(result[0].text)["impact"]
    assert "direct_dependencies" in impact
    assert "indirect_dependencies" in impact
    assert "potential_impact_score" in impact
    assert isinstance(impact["potential_impact_score"], (int, float))
    assert impact["potential_impact_score"] >= 0

async def test_find_similar_entities(graph_manager):
    """Test finding similar entities"""
    # Test relationship pattern similarity
    result = await handle_tool_call(
        "find_similar_entities",
        {
            "entity_name": "class:GraphManager",
            "similarity_type": "relationship_pattern"
        },
        graph_manager
    )
    similar = json.loads(result[0].text)["similar_entities"]
    assert isinstance(similar, list)
    if similar:
        assert "name" in similar[0]
        assert "similarity_score" in similar[0]
        assert "type" in similar[0]
    
    # Test usage pattern similarity
    result = await handle_tool_call(
        "find_similar_entities",
        {
            "entity_name": "class:GraphManager",
            "similarity_type": "usage_pattern"
        },
        graph_manager
    )
    similar = json.loads(result[0].text)["similar_entities"]
    assert isinstance(similar, list)
    
    # Test structural similarity
    result = await handle_tool_call(
        "find_similar_entities",
        {
            "entity_name": "class:GraphManager",
            "similarity_type": "structural"
        },
        graph_manager
    )
    similar = json.loads(result[0].text)["similar_entities"]
    assert isinstance(similar, list)

async def test_analyze_module_dependencies(graph_manager):
    """Test analyzing module dependencies"""
    result = await handle_tool_call(
        "analyze_module_dependencies",
        {
            "module_path": "./code_graph_mcp.py",
            "include_external": True
        },
        graph_manager
    )
    
    module_info = json.loads(result[0].text)
    assert "module_path" in module_info
    assert "entity_count" in module_info
    assert "dependencies" in module_info
    assert isinstance(module_info["dependencies"]["internal"], dict)
    assert isinstance(module_info["dependencies"]["external"], dict)
    assert module_info["entity_count"] > 0

async def test_find_dead_code(graph_manager):
    """Test finding dead code"""
    # Test function scope
    result = await handle_tool_call(
        "find_dead_code",
        {
            "scope": "function",
            "confidence_threshold": 0.8
        },
        graph_manager
    )
    
    dead_code = json.loads(result[0].text)["dead_code"]
    assert isinstance(dead_code, list)
    if dead_code:
        assert "name" in dead_code[0]
        assert "type" in dead_code[0]
        assert "confidence" in dead_code[0]
        assert "used_by_count" in dead_code[0]
    
    # Test class scope
    result = await handle_tool_call(
        "find_dead_code",
        {
            "scope": "class",
            "confidence_threshold": 0.8
        },
        graph_manager
    )
    dead_code = json.loads(result[0].text)["dead_code"]
    assert isinstance(dead_code, list)

async def test_edge_cases(graph_manager):
    """Test edge cases and error handling"""
    # Test non-existent entity
    result = await handle_tool_call(
        "find_code_path",
        {
            "source": "non_existent_entity",
            "target": "also_non_existent",
            "max_depth": 3
        },
        graph_manager
    )
    paths = json.loads(result[0].text)["paths"]
    assert len(paths) == 0
    
    # Test invalid similarity type
    with pytest.raises(ValueError, match="Invalid similarity type"):
        await handle_tool_call(
            "find_similar_entities",
            {
                "entity_name": "class:GraphManager",
                "similarity_type": "invalid_type"
            },
            graph_manager
        )
    
    # Test empty module path
    result = await handle_tool_call(
        "analyze_module_dependencies",
        {
            "module_path": "non_existent_module.py",
            "include_external": True
        },
        graph_manager
    )
    module_info = json.loads(result[0].text)
    assert module_info["entity_count"] == 0 