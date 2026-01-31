/**
 * Main Application Script
 * Coordinates all components of the Walking Route Planner
 */
class WalkingRoutePlanner {
    constructor() {
        this.mapHandler = null;
        this.orchestrateBridge = null;
        this.routeMode = 'circular_loop';
        this.duration = 30;
        this.vibes = {
            greenery: 0.5,
            blue_space: 0,
            introvert_mode: 0,
            extrovert_mode: 0,
            safety_check: 0.5,
            walkability: 0.7
        };
        
        this.init();
    }
    
    init() {
        // Initialize map
        this.mapHandler = new MapHandler('map');
        this.mapHandler.setClickMode('start');
        this.mapHandler.onMarkerSet = this.handleMarkerSet.bind(this);
        
        // Initialize Orchestrate bridge
        this.orchestrateBridge = new OrchestrateBridge(this.mapHandler);
        this.orchestrateBridge.on('routeReceived', this.handleRouteReceived.bind(this));
        this.orchestrateBridge.on('vibesExtracted', this.handleVibesExtracted.bind(this));
        
        // Set up UI event listeners
        this.setupEventListeners();
        
        console.log('Walking Route Planner initialized');
    }
    
    setupEventListeners() {
        // Vibe sliders
        const vibeSliders = ['greenery', 'blue_space', 'introvert_mode', 'extrovert_mode', 'safety_check', 'walkability'];
        vibeSliders.forEach(vibe => {
            const slider = document.getElementById(vibe);
            if (slider) {
                slider.addEventListener('input', (e) => {
                    const value = parseInt(e.target.value, 10) / 100;
                    this.vibes[vibe] = value;
                    
                    const valueDisplay = document.getElementById(`${vibe}-value`);
                    if (valueDisplay) {
                        valueDisplay.textContent = `${Math.round(value * 100)}%`;
                    }
                });
            }
        });
        
        // Route mode buttons
        const modeLoop = document.getElementById('mode-loop');
        const modeP2P = document.getElementById('mode-p2p');
        const durationSelector = document.getElementById('duration-selector');
        
        if (modeLoop) {
            modeLoop.addEventListener('click', () => {
                this.routeMode = 'circular_loop';
                modeLoop.classList.add('active');
                modeP2P?.classList.remove('active');
                durationSelector?.style.setProperty('display', 'block');
                this.mapHandler.setClickMode('start');
                this.mapHandler.clearMarkers();
            });
        }
        
        if (modeP2P) {
            modeP2P.addEventListener('click', () => {
                this.routeMode = 'point_to_point';
                modeP2P.classList.add('active');
                modeLoop?.classList.remove('active');
                durationSelector?.style.setProperty('display', 'none');
                this.mapHandler.setClickMode('start');
                this.mapHandler.clearMarkers();
            });
        }
        
        // Duration slider
        const durationSlider = document.getElementById('duration');
        const durationDisplay = document.getElementById('duration-display');
        if (durationSlider) {
            durationSlider.addEventListener('input', (e) => {
                this.duration = parseInt(e.target.value, 10);
                if (durationDisplay) {
                    durationDisplay.textContent = `${this.duration} min`;
                }
            });
        }
        
        // Generate route button
        const generateBtn = document.getElementById('generate-route-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateRoute());
        }
        
        // My location button
        const myLocationBtn = document.getElementById('my-location-btn');
        if (myLocationBtn) {
            myLocationBtn.addEventListener('click', async () => {
                try {
                    await this.mapHandler.centerOnUserLocation();
                } catch (error) {
                    alert('Could not get your location. Please click on the map to set a starting point.');
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
        
        // Chat input (fallback when Orchestrate not configured)
        const chatInput = document.getElementById('chat-input');
        const chatSend = document.getElementById('chat-send');
        
        if (chatInput && chatSend) {
            const sendMessage = () => {
                const message = chatInput.value.trim();
                if (message) {
                    this.handleChatMessage(message);
                    chatInput.value = '';
                }
            };
            
            chatSend.addEventListener('click', sendMessage);
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        }
    }
    
    handleMarkerSet(coords) {
        console.log('Markers set:', coords);
        // Could auto-trigger route generation here
    }
    
    handleRouteReceived(data) {
        console.log('Route received:', data);
        this.hideLoading();
    }
    
    handleVibesExtracted(vibes) {
        console.log('Vibes extracted:', vibes);
        Object.assign(this.vibes, vibes);
    }
    
    async handleChatMessage(message) {
        // Add user message to chat
        this.addChatMessage(message, 'user');
        
        // Parse natural language
        const parsed = this.orchestrateBridge.parseNaturalLanguage(message);
        console.log('Parsed message:', parsed);
        
        // Update vibes from parsed message
        Object.assign(this.vibes, parsed.vibes);
        this.duration = parsed.duration;
        
        // Update UI
        this.updateVibeSliders();
        
        // Get start location
        const startCoords = this.mapHandler.getStartCoords();
        if (!startCoords) {
            this.addChatMessage(
                "I'd love to plan your route! Please click on the map to set your starting point first.",
                'assistant'
            );
            return;
        }
        
        // Set mode from parsed message
        if (parsed.mode) {
            this.routeMode = parsed.mode;
            this.updateModeButtons();
        }
        
        // Generate route
        this.addChatMessage(
            `Great! I'm planning a ${this.duration}-minute ${this.routeMode === 'circular_loop' ? 'loop' : 'route'} for you. Let me find the best path based on your vibes...`,
            'assistant'
        );
        
        await this.generateRoute();
    }
    
    addChatMessage(text, type) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.innerHTML = `<p>${text}</p>`;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    updateVibeSliders() {
        Object.entries(this.vibes).forEach(([key, value]) => {
            const slider = document.getElementById(key);
            if (slider) {
                slider.value = value * 100;
            }
            const valueDisplay = document.getElementById(`${key}-value`);
            if (valueDisplay) {
                valueDisplay.textContent = `${Math.round(value * 100)}%`;
            }
        });
    }
    
    updateModeButtons() {
        const modeLoop = document.getElementById('mode-loop');
        const modeP2P = document.getElementById('mode-p2p');
        const durationSelector = document.getElementById('duration-selector');
        
        if (this.routeMode === 'circular_loop') {
            modeLoop?.classList.add('active');
            modeP2P?.classList.remove('active');
            durationSelector?.style.setProperty('display', 'block');
        } else {
            modeP2P?.classList.add('active');
            modeLoop?.classList.remove('active');
            durationSelector?.style.setProperty('display', 'none');
        }
    }
    
    showLoading() {
        document.getElementById('loading-overlay')?.classList.remove('hidden');
    }
    
    hideLoading() {
        document.getElementById('loading-overlay')?.classList.add('hidden');
    }
    
    async generateRoute() {
        const startCoords = this.mapHandler.getStartCoords();
        if (!startCoords) {
            alert('Please click on the map to set a starting point');
            return;
        }
        
        // For point-to-point, need destination
        const endCoords = this.mapHandler.getEndCoords();
        if (this.routeMode === 'point_to_point' && !endCoords) {
            alert('Please click on the map to set a destination for point-to-point routing');
            this.mapHandler.setClickMode('end');
            return;
        }
        
        this.showLoading();
        
        try {
            const requestBody = {
                mode: this.routeMode,
                origin: startCoords,
                duration_minutes: this.duration,
                vibes: this.vibes,
                include_narrative: true
            };
            
            if (this.routeMode === 'point_to_point' && endCoords) {
                requestBody.destination = endCoords;
            }
            
            console.log('Sending route request:', requestBody);
            
            const response = await fetch(`${CONFIG.API_BASE_URL}/route`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate route');
            }
            
            const data = await response.json();
            console.log('Route response:', data);
            
            if (data.success && data.geojson) {
                this.mapHandler.renderRoute(data.geojson, data.metadata);
                this.orchestrateBridge.updateRouteInfo(data.metadata);
                
                // Add success message to chat
                if (data.metadata?.transparency_narrative) {
                    this.addChatMessage(
                        `Route generated! ${data.metadata.transparency_narrative}`,
                        'assistant'
                    );
                }
            } else {
                throw new Error('Invalid route response');
            }
            
        } catch (error) {
            console.error('Route generation error:', error);
            this.addChatMessage(
                `Sorry, I couldn't generate a route: ${error.message}. Please try again.`,
                'assistant'
            );
            alert(`Error: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new WalkingRoutePlanner();
});
