import os
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from .ucs import uniform_cost_search
from .graph import NODES, EDGES, build_graph, refresh_graph, get_route_geometry

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    """Serve the main index page."""
    return render_template('index.html')


@app.route('/api/nodes')
def api_nodes():
    """Return all nodes with coordinates and metadata."""
    return jsonify(NODES)


@app.route('/api/graph')
def api_graph():
    """Return the graph adjacency list and edges."""
    try:
        graph = build_graph()
        
        response = {
            "graph": graph,
            "edges": EDGES,
            "nodes": NODES,
            "success": True
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 503


@app.route('/api/solve', methods=['POST'])
def api_solve():
    """
    Run UCS algorithm with the provided start and goal nodes.
    Supports multi-goal nearest hospital search when goal is 'nearest' or empty.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400
            
        start = data.get('start')
        goal = data.get('goal')
        
        # Validate start node
        if not start or start not in NODES:
            return jsonify({"error": "Invalid start node selection"}), 400
        
        # Handle 'nearest' or specific hospital goal
        if goal == "nearest" or not goal:
            goal_target = [nid for nid, node in NODES.items() if node.get('type') == 'hospital']
        elif goal not in NODES:
            return jsonify({"error": "Invalid goal node selection"}), 400
        else:
            goal_target = goal
        
        # Build graph
        graph = build_graph()
        
        # Run UCS
        result = uniform_cost_search(graph, start, goal_target)
        
        if result['found']:
            # Get route geometries for each segment from cache / OSRM
            route_geometry = {}
            path = result['path']
            for i in range(len(path) - 1):
                segment_key = f"{path[i]}->{path[i+1]}"
                route_geometry[segment_key] = get_route_geometry(path[i], path[i+1])
            
            result['route_geometry'] = route_geometry
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/graph/refresh', methods=['GET', 'POST'])
def api_graph_refresh():
    """Force refresh of graph cache and rebuild from OSRM."""
    try:
        graph = refresh_graph()
        return jsonify({
            "success": True,
            "message": "Graph and geometry cache refreshed",
            "graph": graph
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
