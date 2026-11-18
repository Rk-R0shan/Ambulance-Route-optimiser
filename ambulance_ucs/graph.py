import os
import json
import math
import requests

# Define nodes with real Chennai locations
NODES = {
    # ── HOSPITALS ──────────────────────────────────────────────
    "apollo": {
        "name": "Apollo Hospital, Greams Road",
        "lat": 13.0604, "lng": 80.2496,
        "type": "hospital"
    },
    "fortis": {
        "name": "Fortis Malar Hospital, Adyar",
        "lat": 13.0072, "lng": 80.2574,
        "type": "hospital"
    },
    "stanley": {
        "name": "Stanley Government Hospital, Royapuram",
        "lat": 13.1061, "lng": 80.2870,
        "type": "hospital"
    },
    "gggh": {
        "name": "Rajiv Gandhi Govt. General Hospital",
        "lat": 13.0827, "lng": 80.2707,
        "type": "hospital"
    },
    "vijaya": {
        "name": "Vijaya Hospital, Vadapalani",
        "lat": 13.0514, "lng": 80.2121,
        "type": "hospital"
    },

    # ── MAJOR INTERSECTIONS / LANDMARKS ────────────────────────
    "central": {
        "name": "Chennai Central Station",
        "lat": 13.0827, "lng": 80.2707,
        "type": "landmark"
    },
    "egmore": {
        "name": "Egmore Railway Station",
        "lat": 13.0732, "lng": 80.2609,
        "type": "landmark"
    },
    "tnagar": {
        "name": "T. Nagar Bus Terminus",
        "lat": 13.0418, "lng": 80.2341,
        "type": "landmark"
    },
    "adyar": {
        "name": "Adyar Signal Junction",
        "lat": 13.0012, "lng": 80.2565,
        "type": "landmark"
    },
    "anna_nagar": {
        "name": "Anna Nagar Tower Park",
        "lat": 13.0850, "lng": 80.2101,
        "type": "landmark"
    },
    "velachery": {
        "name": "Velachery Bus Terminus",
        "lat": 12.9815, "lng": 80.2180,
        "type": "landmark"
    },
    "mylapore": {
        "name": "Mylapore Tank Junction",
        "lat": 13.0368, "lng": 80.2676,
        "type": "landmark"
    },
    "tambaram": {
        "name": "Tambaram Railway Station",
        "lat": 12.9249, "lng": 80.1000,
        "type": "landmark"
    },
    "chromepet": {
        "name": "Chromepet Junction",
        "lat": 12.9516, "lng": 80.1462,
        "type": "landmark"
    },
    "guindy": {
        "name": "Guindy Metro Station",
        "lat": 13.0067, "lng": 80.2206,
        "type": "landmark"
    },
    "koyambedu": {
        "name": "Koyambedu Bus Stand",
        "lat": 13.0694, "lng": 80.1948,
        "type": "landmark"
    },
    "royapettah": {
        "name": "Royapettah Clock Tower",
        "lat": 13.0524, "lng": 80.2602,
        "type": "landmark"
    },
    "perambur": {
        "name": "Perambur Railway Station",
        "lat": 13.1143, "lng": 80.2485,
        "type": "landmark"
    },
    "madhavaram": {
        "name": "Madhavaram Milk Colony",
        "lat": 13.1490, "lng": 80.2337,
        "type": "landmark"
    },
    "sholinganallur": {
        "name": "Sholinganallur Junction",
        "lat": 12.9010, "lng": 80.2279,
        "type": "landmark"
    },
    "omr": {
        "name": "OMR Toll Plaza",
        "lat": 12.9345, "lng": 80.2298,
        "type": "landmark"
    },
    "porur": {
        "name": "Porur Junction",
        "lat": 13.0358, "lng": 80.1567,
        "type": "landmark"
    },
    "ambattur": {
        "name": "Ambattur Industrial Estate",
        "lat": 13.1143, "lng": 80.1548,
        "type": "landmark"
    },
    "avadi": {
        "name": "Avadi Bus Stand",
        "lat": 13.1152, "lng": 80.0980,
        "type": "landmark"
    },

    # ── EMERGENCY INCIDENT LOCATIONS ───────────────────────────
    "inc_besant": {
        "name": "Emergency — Besant Nagar Beach",
        "lat": 12.9990, "lng": 80.2707,
        "type": "incident"
    },
    "inc_marina": {
        "name": "Emergency — Marina Beach",
        "lat": 13.0500, "lng": 80.2824,
        "type": "incident"
    },
    "inc_vadapalani": {
        "name": "Emergency — Vadapalani Signal",
        "lat": 13.0525, "lng": 80.2121,
        "type": "incident"
    },
    "inc_chromepet": {
        "name": "Emergency — Chromepet Market",
        "lat": 12.9490, "lng": 80.1440,
        "type": "incident"
    },
    "inc_omr": {
        "name": "Emergency — OMR Perungudi",
        "lat": 12.9600, "lng": 80.2450,
        "type": "incident"
    },
    "inc_anna_nagar": {
        "name": "Emergency — Anna Nagar West",
        "lat": 13.0890, "lng": 80.2050,
        "type": "incident"
    },
    "inc_royapuram": {
        "name": "Emergency — Royapuram Fishing Harbour",
        "lat": 13.1100, "lng": 80.2990,
        "type": "incident"
    },
    "inc_tambaram": {
        "name": "Emergency — Tambaram East",
        "lat": 12.9230, "lng": 80.1150,
        "type": "incident"
    },
}

# Predefined road network topology (46 unique bidirectional connections)
EDGES = [
    # Central corridor
    ("central",       "egmore"),
    ("egmore",        "royapettah"),
    ("royapettah",    "mylapore"),
    ("mylapore",      "adyar"),
    ("adyar",         "fortis"),
    ("adyar",         "inc_besant"),

    # Marina / East coast
    ("central",       "inc_marina"),
    ("inc_marina",    "royapettah"),
    ("inc_marina",    "mylapore"),

    # North Chennai
    ("central",       "perambur"),
    ("perambur",      "stanley"),
    ("perambur",      "madhavaram"),
    ("stanley",       "inc_royapuram"),

    # West corridor
    ("egmore",        "tnagar"),
    ("tnagar",        "vijaya"),
    ("tnagar",        "inc_vadapalani"),
    ("tnagar",        "guindy"),
    ("guindy",        "velachery"),
    ("velachery",     "omr"),
    ("omr",           "sholinganallur"),
    ("sholinganallur","inc_omr"),

    # Apollo connections
    ("egmore",        "apollo"),
    ("royapettah",    "apollo"),
    ("apollo",        "mylapore"),

    # Anna Nagar / NW corridor
    ("anna_nagar",    "koyambedu"),
    ("anna_nagar",    "ambattur"),
    ("anna_nagar",    "inc_anna_nagar"),
    ("koyambedu",     "porur"),
    ("koyambedu",     "tnagar"),
    ("ambattur",      "avadi"),
    ("porur",         "guindy"),
    ("porur",         "vijaya"),
    ("vijaya",        "inc_vadapalani"),

    # South Chennai / OMR
    ("guindy",        "chromepet"),
    ("chromepet",     "tambaram"),
    ("chromepet",     "inc_chromepet"),
    ("tambaram",      "inc_tambaram"),
    ("velachery",     "sholinganallur"),
    ("omr",           "fortis"),

    # GGGH connections
    ("central",       "gggh"),
    ("egmore",        "gggh"),

    # Cross links
    ("adyar",         "guindy"),
    ("anna_nagar",    "perambur"),
    ("avadi",         "madhavaram"),
    ("inc_omr",       "omr"),
    ("inc_royapuram", "perambur"),
]

# In-memory caches
_graph_cache = None
_geometry_cache = {}

# Bundled offline cache path
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "data", "chennai_cached_graph.json")


def _load_bundled_fixture():
    """Load pre-cached durations and geometries if available."""
    if os.path.exists(FIXTURE_PATH):
        try:
            with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read bundled fixture: {e}")
    return None


def haversine(lat1, lng1, lat2, lng2):
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns duration in seconds assuming 40 km/h average speed.
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    distance_km = R * c
    
    # Assume 40 km/h average emergency speed
    speed_kmh = 40
    duration_hours = distance_km / speed_kmh
    duration_seconds = duration_hours * 3600
    
    return duration_seconds


def fetch_osrm_durations(node_pairs):
    """
    Fetch travel durations from OSRM table API.
    Computes true directional driving durations for both (n1, n2) and (n2, n1).
    Falls back to bundled fixture or Haversine if OSRM is unavailable.
    """
    result = {}
    
    try:
        unique_nodes = sorted(list(set([n for pair in node_pairs for n in pair])))
        coords = ";".join([f"{NODES[n]['lng']},{NODES[n]['lat']}" for n in unique_nodes])
        url = f"https://router.project-osrm.org/table/v1/driving/{coords}?sources=all&destinations=all&annotations=duration"
        
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != "Ok":
            raise Exception(f"OSRM error: {data.get('message')}")
        
        durations = data.get("durations", [])
        
        for n1, n2 in node_pairs:
            idx1 = unique_nodes.index(n1)
            idx2 = unique_nodes.index(n2)
            
            d_forward = durations[idx1][idx2]
            d_backward = durations[idx2][idx1]
            
            # Sanitize None values with Haversine
            if d_forward is None:
                d_forward = haversine(NODES[n1]["lat"], NODES[n1]["lng"], NODES[n2]["lat"], NODES[n2]["lng"])
            if d_backward is None:
                d_backward = haversine(NODES[n2]["lat"], NODES[n2]["lng"], NODES[n1]["lat"], NODES[n1]["lng"])
                
            result[(n1, n2)] = round(d_forward, 1)
            result[(n2, n1)] = round(d_backward, 1)
        
        return result
    
    except Exception as e:
        print(f"Live OSRM table fetch failed ({e}). Attempting offline fixture / fallback.")
        fixture = _load_bundled_fixture()
        
        for n1, n2 in node_pairs:
            forward_key = f"{n1}->{n2}"
            backward_key = f"{n2}->{n1}"
            
            if fixture and "durations" in fixture:
                d12 = fixture["durations"].get(forward_key)
                d21 = fixture["durations"].get(backward_key)
            else:
                d12 = None
                d21 = None
                
            if d12 is None and n1 in NODES and n2 in NODES:
                d12 = round(haversine(NODES[n1]["lat"], NODES[n1]["lng"], NODES[n2]["lat"], NODES[n2]["lng"]), 1)
            if d21 is None and n1 in NODES and n2 in NODES:
                d21 = round(haversine(NODES[n2]["lat"], NODES[n2]["lng"], NODES[n1]["lat"], NODES[n1]["lng"]), 1)
                
            result[(n1, n2)] = d12
            result[(n2, n1)] = d21
            
        return result


def get_route_geometry(start_node_id, end_node_id):
    """
    Get polyline coordinates from OSRM route API or cache.
    Caches geometries in-memory to prevent repeated network latency and rate limits.
    """
    cache_key = f"{start_node_id}->{end_node_id}"
    
    # 1. Check in-memory cache
    if cache_key in _geometry_cache:
        return _geometry_cache[cache_key]
    
    # 2. Check bundled offline fixture
    fixture = _load_bundled_fixture()
    if fixture and "geometries" in fixture and cache_key in fixture["geometries"]:
        _geometry_cache[cache_key] = fixture["geometries"][cache_key]
        return _geometry_cache[cache_key]
    
    # 3. Query live OSRM Route API
    try:
        start = NODES[start_node_id]
        end = NODES[end_node_id]
        
        url = f"https://router.project-osrm.org/route/v1/driving/{start['lng']},{start['lat']};{end['lng']},{end['lat']}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != "Ok" or not data.get("routes"):
            raise Exception("No route found")
        
        coordinates = data["routes"][0].get("geometry", {}).get("coordinates", [])
        geometry = [[lat, lng] for lng, lat in coordinates]
        _geometry_cache[cache_key] = geometry
        return geometry
    
    except Exception as e:
        print(f"OSRM route fetch failed for {cache_key} ({e}). Using straight line.")
        start = NODES[start_node_id]
        end = NODES[end_node_id]
        straight_line = [
            [start["lat"], start["lng"]],
            [end["lat"], end["lng"]]
        ]
        _geometry_cache[cache_key] = straight_line
        return straight_line


def build_graph(nodes=None, edges=None):
    """
    Build directed adjacency list graph from nodes and edges.
    Captures realistic directional road travel times.
    """
    global _graph_cache
    
    if _graph_cache is not None:
        return _graph_cache
    
    if nodes is None:
        nodes = NODES
    if edges is None:
        edges = EDGES
    
    durations = fetch_osrm_durations(edges)
    
    graph = {node_id: [] for node_id in nodes}
    
    for n1, n2 in edges:
        d12 = durations.get((n1, n2))
        d21 = durations.get((n2, n1))
        
        if d12 is None:
            d12 = haversine(nodes[n1]["lat"], nodes[n1]["lng"], nodes[n2]["lat"], nodes[n2]["lng"])
        if d21 is None:
            d21 = haversine(nodes[n2]["lat"], nodes[n2]["lng"], nodes[n1]["lat"], nodes[n1]["lng"])
            
        graph[n1].append((n2, d12))
        graph[n2].append((n1, d21))
    
    _graph_cache = graph
    return graph


def refresh_graph():
    """Force refresh of graph and geometry cache."""
    global _graph_cache, _geometry_cache
    _graph_cache = None
    _geometry_cache = {}
    return build_graph()
