import heapq

def uniform_cost_search(graph, start, goal):
    """
    Uniform Cost Search implementation using heapq.
    
    Args:
        graph: dict of {node_id: [(neighbor_id, cost), ...]}
        start: starting node_id
        goal: goal node_id (str) or iterable of goal node_ids (set/list)
    
    Returns:
        dict with:
        - path: list of node ids from start to goal
        - goal: matched goal node id (str) or None
        - total_cost_seconds: float (total time in seconds)
        - total_cost_minutes: float (total time in minutes)
        - explored_order: list of dicts with {node, cumulative_cost, path_so_far, frontier_snapshot}
        - found: bool (True if goal was reached)
    """
    goals = {goal} if isinstance(goal, str) else set(goal)
    
    # Priority queue entries: (cost, counter, node, path)
    # Using insertion counter prevents comparing paths/nodes when costs tie
    frontier = []
    counter = 0
    heapq.heappush(frontier, (0, counter, start, [start]))
    explored = set()
    explored_order = []

    while frontier:
        # Snapshot current frontier (top 6 items sorted by cost) for live visualization
        frontier_snapshot = [
            {"node": item[2], "cost": round(item[0] / 60, 2)}
            for item in sorted(frontier)[:6]
        ]
        
        cost, _, node, path = heapq.heappop(frontier)
        
        # Skip if already explored
        if node in explored:
            continue
        
        explored.add(node)
        explored_order.append({
            "node": node,
            "cumulative_cost": round(cost / 60, 2),
            "path_so_far": path[:],
            "frontier_snapshot": frontier_snapshot
        })
        
        # Check if goal reached
        if node in goals:
            return {
                "path": path,
                "goal": node,
                "total_cost_seconds": cost,
                "total_cost_minutes": round(cost / 60, 2),
                "explored_order": explored_order,
                "found": True
            }
        
        # Add neighbors to frontier
        for neighbor, weight in graph.get(node, []):
            if neighbor not in explored:
                counter += 1
                heapq.heappush(frontier, 
                    (cost + weight, counter, neighbor, path + [neighbor]))

    return {
        "path": [],
        "goal": None,
        "total_cost_seconds": 0,
        "total_cost_minutes": 0,
        "explored_order": explored_order,
        "found": False
    }
