/**
 * Main Application Script - WebSocket Real-time Architecture
 * 
 * WebSocket-enabled version for instant route display.
 * The flow is:
 * 1. User clicks on map → Location stored + WebSocket connected
 * 2. WebSocket listens for route_ready events
 * 3. User chats with Orchestrate (provides session_id)
 * 4. Orchestrate calls /execute with session_id
 * 5. Backend broadcasts route via WebSocket
 * 6. Route appears INSTANTLY on map - no button click needed!
 */

class WalkingRoutePlanner {
    constructor() {
        this.mapHandler = null;
        this.orchestrateBridge = null;
        this.selectedLocation = null;
        this.websocket = null;
        this.isWaitingForRoute = false;

        this.init();
    }

    init() {
        // Initialize map
        this.mapHandler = new MapHandler('map');
        this.mapHandler.setClickMode('start');
        this.mapHandler.onMarkerSet = this.handleMarkerSet.bind(this);

        // Initialize Orchestrate bridge (for fallback)
        this.orchestrateBridge = new OrchestrateBridge(this.mapHandler);
        this.orchestrateBridge.on('routeReceived', this.handleRouteReceived.bind(this));

        // Set up UI event listeners
        this.setupEventListeners();
        // Chat listeners removed

        console.log('Walking Route Planner initialized - WebSocket mode');
        console.log('Session ID:', CONFIG.SESSION_ID);
    }

    setupEventListeners() {
        // My location button
        const myLocationBtn = document.getElementById('my-location-btn');
        if (myLocationBtn) {
            myLocationBtn.addEventListener('click', async () => {
                try {
                    const coords = await this.mapHandler.centerOnUserLocation();
                    this.selectedLocation = coords;
                    await this.sendLocationToBackend(coords);
                    this.hideLocationHint();
                } catch (error) {
                    console.error('Could not get location:', error);
                    alert('Could not get your location. Please click on the map instead.');
                }
            });
        }

        // Close route info button
        const closeRouteInfo = document.getElementById('close-route-info');
        if (closeRouteInfo) {
            closeRouteInfo.addEventListener('click', () => {
                document.getElementById('route-info')?.classList.add('hidden');
            });
        }

        // Listen for location selected events from map
        window.addEventListener('locationSelected', async (e) => {
            this.selectedLocation = e.detail;
            await this.sendLocationToBackend(e.detail);
            this.hideLocationHint();
        });
    }

    handleMarkerSet(coords) {
        console.log('Marker set:', coords);
        if (coords.start) {
            this.selectedLocation = coords.start;
        }
    }

    async sendLocationToBackend(coords) {
        console.log('Sending location to backend and connecting WebSocket:', coords);

        try {
            // Store location via REST API
            const response = await fetch(`${CONFIG.API_BASE_URL}/set-location`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: CONFIG.SESSION_ID,
                    lat: coords.lat,
                    lon: coords.lon
                })
            });

            if (!response.ok) {
                console.error('Failed to store location:', await response.text());
                return;
            }

            console.log('Location stored. Connecting WebSocket...');

            // Connect WebSocket for real-time updates
            this.connectWebSocket();

            // Show the session info UI
            this.showSessionInfo();

        } catch (error) {
            console.error('Error:', error);
        }
    }

    connectWebSocket() {
        // Convert HTTP URL to WebSocket URL
        const wsUrl = CONFIG.API_BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://');
        const fullUrl = `${wsUrl}/ws/${CONFIG.SESSION_ID}`;

        console.log('Connecting WebSocket:', fullUrl);

        this.websocket = new WebSocket(fullUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected! Ready for real-time route updates.');
            this.updateStatus('🟢 Connected! Chat with the AI and your route will appear automatically.');
        };

        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('WebSocket message received:', message);

            if (message.type === 'route_ready') {
                this.handleWebSocketRoute(message.data);
            }
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('🔴 Connection error. Please refresh the page.');
        };

        this.websocket.onclose = () => {
            console.log('WebSocket closed');
            this.updateStatus('🟡 Disconnected. Reconnecting...');
            // Auto-reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    handleWebSocketRoute(routeData) {
        console.log('Route received via WebSocket:', routeData);

        // Hide loading
        this.hideLoading();
        this.isWaitingForRoute = false;

        // Update status
        this.updateStatus('✅ Route received! See your path on the map.');

        // Render route on map
        if (this.mapHandler && routeData.geojson) {
            this.mapHandler.renderRoute(routeData.geojson, routeData.metadata);
        }

        // Update route info panel
        if (this.orchestrateBridge) {
            this.orchestrateBridge.updateRouteInfo(routeData.metadata);
        }

        // Show route info
        document.getElementById('route-info')?.classList.remove('hidden');
    }

    showSessionInfo() {
        const box = document.getElementById('session-id-box');
        const display = document.getElementById('session-id-display');

        if (box && display) {
            display.textContent = CONFIG.SESSION_ID;
            box.style.display = 'block';

            // Auto-copy
            this.copySessionId();

            // Update status
            this.updateStatus('⏳ Ready! Copy your session ID and chat with the AI.');
        }
    }

    updateStatus(message) {
        const statusEl = document.getElementById('route-status');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.style.display = 'block';
        }
    }

    copySessionId() {
        navigator.clipboard.writeText(CONFIG.SESSION_ID).then(() => {
            const btn = document.getElementById('copy-session-btn');
            if (btn) {
                btn.textContent = '✅ Copied!';
                setTimeout(() => {
                    btn.textContent = '📋 Copy';
                }, 2000);
            }
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    hideLocationHint() {
        const hint = document.getElementById('location-hint');
        if (hint) {
            hint.classList.add('hidden');
        }
    }

    showLoading() {
        document.getElementById('loading-overlay')?.classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-overlay')?.classList.add('hidden');
    }

    handleRouteReceived(data) {
        // This is for fallback mode (not WebSocket)
        console.log('Route received (fallback):', data);
        this.hideLoading();
    }

    // Chat methods removed to enforce external Orchestrate workflow
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new WalkingRoutePlanner();
});
