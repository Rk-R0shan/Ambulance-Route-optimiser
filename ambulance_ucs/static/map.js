// Global state
var map;
var baseNetworkLayer;
var searchLayer;
var markers = {};
var appData = {
    nodes: {},
    edges: [],
    graph: {},
    loading: false
};

var animationRunning = false;
var cancelAnimationRequested = false;
var animationSpeedMs = 300;
var currentStepIndex = 0;
var cachedSolveResult = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    initializeMap();
    await loadGraphData();
    setupEventListeners();
});

// Initialize Leaflet map
function initializeMap() {
    if (typeof L === 'undefined') {
        console.error('Leaflet JS is not loaded');
        showToast('Leaflet library failed to load from CDN. Check your internet connection.');
        return;
    }
    
    const chennaiBounds = [13.0450, 80.2200];
    map = L.map('map').setView(chennaiBounds, 12);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Dedicated layers to prevent wiping out road network during route clearing
    baseNetworkLayer = L.layerGroup().addTo(map);
    searchLayer = L.layerGroup().addTo(map);

    // Invalidate size after layout settles to guarantee complete tile rendering
    setTimeout(() => {
        if (map) map.invalidateSize();
    }, 250);
}

// Load graph data from backend
async function loadGraphData() {
    showSpinner(true);
    try {
        const response = await fetch('/api/graph');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load graph');
        }
        
        appData.nodes = data.nodes;
        appData.edges = data.edges;
        appData.graph = data.graph;
        
        plotNodes();
        drawEdges();
        populateSelects();
        
        const totalNodes = Object.keys(appData.nodes).length;
        document.getElementById('stat-explored').textContent = `0 / ${totalNodes}`;
        
        showSpinner(false);
    } catch (error) {
        console.error('Error loading graph:', error);
        showToast(`Error: ${error.message}`);
        showSpinner(false);
    }
}

// Plot all nodes as markers
function plotNodes() {
    for (const [nodeId, nodeData] of Object.entries(appData.nodes)) {
        const icon = createCustomIcon(nodeData.type);
        const marker = L.marker([nodeData.lat, nodeData.lng], { icon })
            .bindPopup(`<strong>${nodeData.name}</strong><br>Type: ${nodeData.type.toUpperCase()}`)
            .addTo(map);
        
        markers[nodeId] = {
            marker: marker,
            type: nodeData.type,
            lat: nodeData.lat,
            lng: nodeData.lng,
            name: nodeData.name
        };
    }
}

// Create custom icon based on node type
function createCustomIcon(type) {
    let htmlContent = '';
    let iconClass = '';
    
    switch (type) {
        case 'hospital':
            htmlContent = 'H';
            iconClass = 'marker-icon-hospital';
            break;
        case 'incident':
            htmlContent = '!';
            iconClass = 'marker-icon-incident';
            break;
        case 'landmark':
            htmlContent = '•';
            iconClass = 'marker-icon-landmark';
            break;
        default:
            htmlContent = '•';
            iconClass = 'marker-icon-landmark';
    }
    
    return L.divIcon({
        html: `<div class="${iconClass}">${htmlContent}</div>`,
        className: 'custom-marker',
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16]
    });
}

// Draw static edges as dashed polylines into baseNetworkLayer
function drawEdges() {
    baseNetworkLayer.clearLayers();
    
    appData.edges.forEach(([node1, node2]) => {
        if (appData.nodes[node1] && appData.nodes[node2]) {
            const n1 = appData.nodes[node1];
            const n2 = appData.nodes[node2];
            
            const polyline = L.polyline(
                [[n1.lat, n1.lng], [n2.lat, n2.lng]],
                {
                    color: '#999',
                    weight: 2,
                    opacity: 0.55,
                    dashArray: '5, 5'
                }
            ).addTo(baseNetworkLayer);
            
            const durationForward = calculateDuration(node1, node2);
            const durationBackward = calculateDuration(node2, node1);
            
            polyline.bindTooltip(
                `<strong>Road Segment:</strong><br>` +
                `${n1.name} ➔ ${n2.name}: ${(durationForward / 60).toFixed(1)} min<br>` +
                `${n2.name} ➔ ${n1.name}: ${(durationBackward / 60).toFixed(1)} min`
            );
        }
    });
}

// Calculate travel duration between two nodes in seconds
function calculateDuration(node1, node2) {
    const graph = appData.graph;
    if (graph[node1]) {
        for (const [neighbor, duration] of graph[node1]) {
            if (neighbor === node2) {
                return duration;
            }
        }
    }
    return 0;
}

// Populate dropdown selects
function populateSelects() {
    const startSelect = document.getElementById('start-node');
    const goalSelect = document.getElementById('goal-node');
    
    startSelect.innerHTML = '<option value="">Select incident location...</option>';
    goalSelect.innerHTML = '<option value="nearest">⚡ Nearest Hospital (Automatic)</option>';
    
    // Incidents for start
    const incidents = Object.entries(appData.nodes).filter(([, data]) => data.type === 'incident');
    incidents.forEach(([id, data]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = data.name;
        startSelect.appendChild(option);
    });
    
    // Hospitals for goal
    const hospitals = Object.entries(appData.nodes).filter(([, data]) => data.type === 'hospital');
    hospitals.forEach(([id, data]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = data.name;
        goalSelect.appendChild(option);
    });
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('btn-run').addEventListener('click', runUCS);
    document.getElementById('btn-step').addEventListener('click', stepManual);
    document.getElementById('btn-reset').addEventListener('click', resetMap);
    document.getElementById('btn-random').addEventListener('click', randomEmergency);
    
    const speedRange = document.getElementById('speed-range');
    const speedDisplay = document.getElementById('speed-display');
    if (speedRange && speedDisplay) {
        speedRange.addEventListener('input', (e) => {
            animationSpeedMs = parseInt(e.target.value, 10);
            speedDisplay.textContent = `${animationSpeedMs}ms`;
        });
    }
}

// Fetch solve result from API
async function fetchSolveResult(startNode, goalNode) {
    const response = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start: startNode, goal: goalNode })
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Solve request failed');
    }
    
    return await response.json();
}

// Run UCS algorithm with animated exploration
async function runUCS() {
    const startNode = document.getElementById('start-node').value;
    const goalNode = document.getElementById('goal-node').value;
    
    if (!startNode) {
        showToast('Please select an emergency incident location');
        return;
    }
    
    if (goalNode && goalNode !== 'nearest' && startNode === goalNode) {
        showToast('Start and goal must be different locations');
        return;
    }
    
    // Stop any active animation
    cancelAnimationRequested = true;
    await new Promise(r => setTimeout(r, 50));
    cancelAnimationRequested = false;
    
    setControlsDisabled(true);
    
    try {
        const result = await fetchSolveResult(startNode, goalNode);
        
        if (!result.found) {
            showToast('No path found to any destination hospital');
            setControlsDisabled(false);
            return;
        }
        
        cachedSolveResult = result;
        currentStepIndex = 0;
        
        // Clear previous search overlays and reset node markers
        clearPreviousVisualization();
        
        // Update stats
        updateStats(result);
        
        // Animate exploration
        await animateExploration(result);
        
    } catch (error) {
        console.error('Error running UCS:', error);
        showToast(`Error: ${error.message}`);
    } finally {
        setControlsDisabled(false);
        document.getElementById('btn-reset').disabled = false;
    }
}

// Animate exploration step by step
async function animateExploration(result) {
    animationRunning = true;
    const exploredOrder = result.explored_order;
    
    for (let i = currentStepIndex; i < exploredOrder.length; i++) {
        if (cancelAnimationRequested) {
            animationRunning = false;
            return;
        }
        
        await new Promise(resolve => setTimeout(resolve, animationSpeedMs));
        
        if (cancelAnimationRequested) {
            animationRunning = false;
            return;
        }
        
        executeExplorationStep(exploredOrder[i], i, exploredOrder.length);
        currentStepIndex = i + 1;
    }
    
    // Draw final optimal path once exploration completes
    if (!cancelAnimationRequested) {
        await drawOptimalPath(result.path, result.route_geometry);
    }
    animationRunning = false;
}

// Execute a single step of exploration (shared by animate and manual step)
function executeExplorationStep(step, index, totalSteps) {
    const nodeId = step.node;
    
    // Update marker to explored (green ✓)
    if (markers[nodeId]) {
        const icon = L.divIcon({
            html: '<div class="marker-icon-explored">✓</div>',
            className: 'custom-marker',
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            popupAnchor: [0, -16]
        });
        markers[nodeId].marker.setIcon(icon);
    }
    
    // Add to step log
    addStepLog(step, index);
    
    // Update priority queue with the true frontier snapshot
    updatePriorityQueue(step);
    
    // Draw path so far as light green polyline in searchLayer
    if (step.path_so_far && step.path_so_far.length > 1) {
        const pathCoords = step.path_so_far.map(id => {
            const node = appData.nodes[id];
            return [node.lat, node.lng];
        });
        
        L.polyline(pathCoords, {
            color: '#4caf50',
            weight: 2,
            opacity: 0.35,
            dashArray: '8, 4'
        }).addTo(searchLayer);
    }
    
    const totalNodes = Object.keys(appData.nodes).length;
    document.getElementById('stat-explored').textContent = `${index + 1} / ${totalNodes}`;
}

// Manual step-by-step exploration
async function stepManual() {
    const startNode = document.getElementById('start-node').value;
    const goalNode = document.getElementById('goal-node').value;
    
    if (!startNode) {
        showToast('Please select an emergency incident location');
        return;
    }
    
    // If not cached or starting fresh, fetch solution first
    if (!cachedSolveResult || currentStepIndex === 0) {
        setControlsDisabled(true);
        try {
            const result = await fetchSolveResult(startNode, goalNode);
            if (!result.found) {
                showToast('No path found to any destination hospital');
                setControlsDisabled(false);
                return;
            }
            cachedSolveResult = result;
            currentStepIndex = 0;
            clearPreviousVisualization();
            updateStats(result);
        } catch (error) {
            showToast(`Error: ${error.message}`);
            setControlsDisabled(false);
            return;
        } finally {
            setControlsDisabled(false);
            document.getElementById('btn-reset').disabled = false;
        }
    }
    
    const exploredOrder = cachedSolveResult.explored_order;
    
    if (currentStepIndex < exploredOrder.length) {
        executeExplorationStep(exploredOrder[currentStepIndex], currentStepIndex, exploredOrder.length);
        currentStepIndex++;
        
        // If reached the last step, draw the optimal path
        if (currentStepIndex === exploredOrder.length) {
            await drawOptimalPath(cachedSolveResult.path, cachedSolveResult.route_geometry);
            const queueDiv = document.getElementById('priority-queue');
            queueDiv.innerHTML = '<div class="queue-item" style="border-left-color: #4caf50;">★ Goal Hospital Reached!</div>';
        }
    } else {
        showToast('Exploration already complete. Click Reset to start over.');
    }
}

// Draw optimal path on map with real road geometry
async function drawOptimalPath(path, routeGeometry) {
    if (!path || path.length < 2) return;
    
    for (let i = 0; i < path.length - 1; i++) {
        const segment = `${path[i]}->${path[i + 1]}`;
        const coords = (routeGeometry && routeGeometry[segment]) || [
            [appData.nodes[path[i]].lat, appData.nodes[path[i]].lng],
            [appData.nodes[path[i + 1]].lat, appData.nodes[path[i + 1]].lng]
        ];
        
        L.polyline(coords, {
            color: '#ff9800',
            weight: 5,
            opacity: 0.95,
            lineJoin: 'round'
        }).addTo(searchLayer);
    }
    
    // Highlight optimal path nodes with glowing stars
    path.forEach(nodeId => {
        if (markers[nodeId]) {
            const icon = L.divIcon({
                html: '<div class="marker-icon-optimal">★</div>',
                className: 'custom-marker',
                iconSize: [34, 34],
                iconAnchor: [17, 17],
                popupAnchor: [0, -16]
            });
            markers[nodeId].marker.setIcon(icon);
        }
    });
}

// Update statistics panel
function updateStats(result) {
    const pathStr = result.path.map(id => appData.nodes[id]?.name || id).join(' ➔ ');
    document.getElementById('stat-path').textContent = pathStr || '—';
    document.getElementById('stat-time').textContent = `${result.total_cost_minutes.toFixed(1)} min (${Math.round(result.total_cost_seconds)}s)`;
    
    const totalNodes = Object.keys(appData.nodes).length;
    document.getElementById('stat-explored').textContent = `${result.explored_order.length} / ${totalNodes}`;
}

// Add entry to step log
function addStepLog(step, index) {
    const stepLog = document.getElementById('step-log');
    
    if (stepLog.querySelector('em')) {
        stepLog.innerHTML = '';
    }
    
    const entry = document.createElement('div');
    entry.className = 'log-entry current';
    
    // Remove highlight from previous entries
    const prev = stepLog.querySelectorAll('.log-entry.current');
    prev.forEach(el => el.classList.remove('current'));
    
    const nodeName = appData.nodes[step.node]?.name || step.node;
    entry.textContent = `Step ${index + 1}: Popped "${nodeName}" (Cost: ${step.cumulative_cost} min)`;
    stepLog.appendChild(entry);
    stepLog.scrollTop = stepLog.scrollHeight;
}

// Update priority queue display with the actual min-heap frontier
function updatePriorityQueue(step) {
    const queueDiv = document.getElementById('priority-queue');
    queueDiv.innerHTML = '';
    
    const snapshot = step.frontier_snapshot || [];
    
    if (snapshot.length === 0) {
        queueDiv.innerHTML = '<em>Queue empty</em>';
        return;
    }
    
    snapshot.forEach((item, idx) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'queue-item' + (idx === 0 ? ' current' : '');
        const nodeName = appData.nodes[item.node]?.name || item.node;
        itemDiv.textContent = `[${idx + 1}] ${nodeName}: ${item.cost} min`;
        queueDiv.appendChild(itemDiv);
    });
}

// Reset map and state to initial view
function resetMap() {
    cancelAnimationRequested = true;
    animationRunning = false;
    currentStepIndex = 0;
    cachedSolveResult = null;
    
    clearPreviousVisualization();
    
    document.getElementById('step-log').innerHTML = '<p><em>Select an incident and click Run UCS</em></p>';
    document.getElementById('priority-queue').innerHTML = '<em>Queue empty</em>';
    document.getElementById('stat-path').textContent = '—';
    document.getElementById('stat-time').textContent = '—';
    
    const totalNodes = Object.keys(appData.nodes).length;
    document.getElementById('stat-explored').textContent = `0 / ${totalNodes}`;
    
    setControlsDisabled(false);
    document.getElementById('btn-reset').disabled = true;
}

// Clear dynamic search visualizations while preserving background road network
function clearPreviousVisualization() {
    searchLayer.clearLayers();
    
    // Restore original marker icons
    for (const [nodeId, markerData] of Object.entries(markers)) {
        const nodeInfo = appData.nodes[nodeId];
        const icon = createCustomIcon(nodeInfo.type);
        markerData.marker.setIcon(icon);
    }
}

// Random emergency incident selection
async function randomEmergency() {
    const incidents = Object.entries(appData.nodes).filter(([, data]) => data.type === 'incident');
    const hospitals = Object.entries(appData.nodes).filter(([, data]) => data.type === 'hospital');
    
    if (incidents.length === 0) {
        showToast('No incidents available');
        return;
    }
    
    const randomIncident = incidents[Math.floor(Math.random() * incidents.length)][0];
    document.getElementById('start-node').value = randomIncident;
    
    // 50% chance of nearest automatic, 50% chance of random specific hospital
    if (Math.random() < 0.5 && hospitals.length > 0) {
        const randomHospital = hospitals[Math.floor(Math.random() * hospitals.length)][0];
        document.getElementById('goal-node').value = randomHospital;
    } else {
        document.getElementById('goal-node').value = 'nearest';
    }
    
    await runUCS();
}

// Enable/disable form controls
function setControlsDisabled(disabled) {
    document.getElementById('btn-run').disabled = disabled;
    document.getElementById('btn-random').disabled = disabled;
    document.getElementById('start-node').disabled = disabled;
    document.getElementById('goal-node').disabled = disabled;
}

// Show/hide loading spinner
function showSpinner(show) {
    const spinner = document.getElementById('spinner');
    if (show) {
        spinner.classList.remove('hidden');
    } else {
        spinner.classList.add('hidden');
    }
}

// Show toast notification
function showToast(message) {
    const toast = document.getElementById('error-toast');
    const messageEl = document.getElementById('toast-message');
    messageEl.textContent = message;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3500);
}
