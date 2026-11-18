"""
Comprehensive unit and integration test suite for Ambulance Route Optimization.
Tests core UCS algorithm, graph building, and API endpoints using Flask test_client (in-memory).
Can be executed with: python test_system.py or pytest test_system.py
"""
import sys
import os

# Add parent directory to path so imports work from anywhere
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ambulance_ucs.ucs import uniform_cost_search
from ambulance_ucs.graph import NODES, EDGES, build_graph, haversine
from ambulance_ucs.app import app


def test_ucs_basic():
    """Unit Test: Uniform Cost Search finds optimal path on mock graph"""
    print("TEST 1: UCS Algorithm - Basic Optimization")
    mock_graph = {
        "A": [("B", 10), ("C", 5)],
        "B": [("D", 15)],
        "C": [("B", 2), ("D", 20)],
        "D": []
    }
    # Path A -> C (5) -> B (7) -> D (22) should beat A -> B (10) -> D (25)
    res = uniform_cost_search(mock_graph, "A", "D")
    assert res["found"] is True, "Path should be found"
    assert res["path"] == ["A", "C", "B", "D"], f"Expected optimal path ['A', 'C', 'B', 'D'], got {res['path']}"
    assert res["total_cost_seconds"] == 22, f"Expected cost 22, got {res['total_cost_seconds']}"
    print("  ✓ Optimal path correctly found via cheapest route A -> C -> B -> D")


def test_ucs_multi_goal():
    """Unit Test: UCS Multi-Goal (Nearest Goal) Search"""
    print("\nTEST 2: UCS Algorithm - Multi-Goal (Nearest Target)")
    mock_graph = {
        "Incident": [("Junction_1", 300), ("Junction_2", 150)],
        "Junction_1": [("Hospital_Far", 200)],
        "Junction_2": [("Hospital_Near", 100), ("Hospital_Far", 500)],
        "Hospital_Far": [],
        "Hospital_Near": []
    }
    hospitals = {"Hospital_Far", "Hospital_Near"}
    res = uniform_cost_search(mock_graph, "Incident", hospitals)
    assert res["found"] is True
    assert res["goal"] == "Hospital_Near", f"Expected nearest goal 'Hospital_Near', got {res['goal']}"
    assert res["path"] == ["Incident", "Junction_2", "Hospital_Near"]
    assert res["total_cost_seconds"] == 250
    print("  ✓ Nearest goal correctly resolved to Hospital_Near (250s vs 500s)")


def test_ucs_unreachable_and_snapshots():
    """Unit Test: UCS handles unreachable nodes and creates valid frontier snapshots"""
    print("\nTEST 3: UCS Algorithm - Unreachable Goal & Frontier Snapshots")
    mock_graph = {
        "Start": [("A", 100)],
        "A": [],
        "Unreachable": []
    }
    res = uniform_cost_search(mock_graph, "Start", "Unreachable")
    assert res["found"] is False
    assert res["path"] == []
    assert len(res["explored_order"]) == 2  # Start and A explored
    
    # Verify frontier snapshots exist in explored order
    for step in res["explored_order"]:
        assert "frontier_snapshot" in step, "Frontier snapshot missing from step"
        assert isinstance(step["frontier_snapshot"], list)
    print("  ✓ Unreachable node gracefully handled and frontier snapshots verified")


def test_graph_integrity():
    """Unit Test: Validate Chennai graph topology and absence of duplicate multi-edges"""
    print("\nTEST 4: Graph Topology & Deduplication")
    assert len(NODES) == 32, f"Expected 32 nodes, got {len(NODES)}"
    assert len(EDGES) == 46, f"Expected 46 unique edges, got {len(EDGES)}"
    
    # Check that no edge pair is duplicated in reverse
    edge_pairs = set()
    for n1, n2 in EDGES:
        pair = tuple(sorted([n1, n2]))
        assert pair not in edge_pairs, f"Duplicate edge detected: ({n1}, {n2})"
        edge_pairs.add(pair)
    
    # Build graph
    graph = build_graph()
    assert len(graph) == 32
    
    # Check that adjacency lists do not contain duplicate neighbors
    for node, neighbors in graph.items():
        neighbor_ids = [n for n, w in neighbors]
        assert len(neighbor_ids) == len(set(neighbor_ids)), f"Duplicate neighbor in graph for node {node}: {neighbor_ids}"
    
    print("  ✓ Graph topology verified: 32 nodes, 46 unique bidirectional connections, 0 duplicate multi-edges")


def test_api_endpoints_in_memory():
    """Integration Test: Flask API endpoints using in-memory test client"""
    print("\nTEST 5: Flask API Endpoints (In-Memory Test Client)")
    client = app.test_client()
    
    # 1. Main index page
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert b"Ambulance Route Optimizer" in res_index.data
    print("  ✓ GET / returns 200 and loads UI")
    
    # 2. Nodes endpoint
    res_nodes = client.get("/api/nodes")
    assert res_nodes.status_code == 200
    nodes_data = res_nodes.get_json()
    assert len(nodes_data) == 32
    print(f"  ✓ GET /api/nodes returns 200 with {len(nodes_data)} locations")
    
    # 3. Graph endpoint
    res_graph = client.get("/api/graph")
    assert res_graph.status_code == 200
    graph_data = res_graph.get_json()
    assert graph_data["success"] is True
    assert len(graph_data["edges"]) == 46
    print("  ✓ GET /api/graph returns 200 with adjacency graph and 46 edges")
    
    # 4. Solve endpoint - Specific Goal
    payload = {"start": "inc_marina", "goal": "apollo"}
    res_solve = client.post("/api/solve", json=payload)
    assert res_solve.status_code == 200
    solve_data = res_solve.get_json()
    assert solve_data["found"] is True
    assert solve_data["path"][0] == "inc_marina"
    assert solve_data["path"][-1] == "apollo"
    assert len(solve_data["route_geometry"]) > 0
    assert len(solve_data["explored_order"][0]["frontier_snapshot"]) > 0
    print(f"  ✓ POST /api/solve (inc_marina -> apollo): Path found in {solve_data['total_cost_minutes']:.1f} min")
    
    # 5. Solve endpoint - Nearest Hospital Automatic
    payload_nearest = {"start": "inc_besant", "goal": "nearest"}
    res_nearest = client.post("/api/solve", json=payload_nearest)
    assert res_nearest.status_code == 200
    nearest_data = res_nearest.get_json()
    assert nearest_data["found"] is True
    chosen_hospital = nearest_data["path"][-1]
    assert NODES[chosen_hospital]["type"] == "hospital"
    print(f"  ✓ POST /api/solve (inc_besant -> nearest): Automatically routed to {NODES[chosen_hospital]['name']}")
    
    # 6. Solve endpoint - Error validation
    res_bad = client.post("/api/solve", json={"start": "fake_node", "goal": "apollo"})
    assert res_bad.status_code == 400
    print("  ✓ POST /api/solve rejects invalid node with HTTP 400")
    
    # 7. Graph refresh endpoint
    res_refresh = client.get("/api/graph/refresh")
    assert res_refresh.status_code == 200
    assert res_refresh.get_json()["success"] is True
    print("  ✓ GET /api/graph/refresh returns 200")


def main():
    print("=" * 60)
    print("AMBULANCE ROUTE OPTIMIZATION - TEST SUITE")
    print("=" * 60)
    
    try:
        test_ucs_basic()
        test_ucs_multi_goal()
        test_ucs_unreachable_and_snapshots()
        test_graph_integrity()
        test_api_endpoints_in_memory()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED SUCCESSFULLY (5/5 suites operational)")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
