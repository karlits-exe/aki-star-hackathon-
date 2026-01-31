/**
 * Orchestrate Bridge - Handles communication between chat and map
 * 
 * This module implements the "handshake" between the watsonx Orchestrate
 * embedded chat and the map visualization. It detects when the agent
 * outputs route data and triggers map rendering.
 */
class OrchestrateBridge {
    constructor(mapHandler) {
        this.mapHandler = mapHandler;
        this.observers = [];
        this.pendingRouteData = null;
        
        this.init();
    }
    
    init() {
        // Set up mutation observer to watch for chat messages
        this.setupChatObserver();
        
        // Set up message listener for postMessage communication
        window.addEventListener('message', this.handlePostMessage.bind(this));
        
        console.log('Orchestrate Bridge initialized');
    }
    
    /**
     * Watch for new messages in the chat container that might contain route data
     */
    setupChatObserver() {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;
        
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        this.checkForRouteData(node);
                    }
                });
            });
        });
        
        observer.observe(chatContainer, {
            childList: true,
            subtree: true
        });
        
        this.observers.push(observer);
    }
    
    /**
     * Check if a DOM element contains route data (JSON code block)
     */
    checkForRouteData(element) {
        // Look for code blocks or JSON data
        const text = element.textContent || '';
        
        // Pattern 1: Look for ```json code blocks
        const jsonBlockMatch = text.match(/```json\s*([\s\S]*?)```/);
        if (jsonBlockMatch) {
            try {
                const data = JSON.parse(jsonBlockMatch[1]);
                if (this.isRouteResponse(data)) {
                    this.handleRouteData(data);
                    return;
                }
            } catch (e) {
                console.warn('Failed to parse JSON block:', e);
            }
        }
        
        // Pattern 2: Look for route_data markers
        const routeDataMatch = text.match(/\[ROUTE_DATA\]([\s\S]*?)\[\/ROUTE_DATA\]/);
        if (routeDataMatch) {
            try {
                const data = JSON.parse(routeDataMatch[1]);
                if (this.isRouteResponse(data)) {
                    this.handleRouteData(data);
                    return;
                }
            } catch (e) {
                console.warn('Failed to parse route data:', e);
            }
        }
        
        // Pattern 3: Try to find any JSON object that looks like a route response
        const jsonMatch = text.match(/\{[\s\S]*"geojson"[\s\S]*\}/);
        if (jsonMatch) {
            try {
                const data = JSON.parse(jsonMatch[0]);
                if (this.isRouteResponse(data)) {
                    this.handleRouteData(data);
                    return;
                }
            } catch (e) {
                // Not valid JSON, ignore
            }
        }
    }
    
    /**
     * Validate that data looks like a route response
     */
    isRouteResponse(data) {
        return (
            data &&
            data.geojson &&
            data.geojson.type === 'FeatureCollection' &&
            Array.isArray(data.geojson.features)
        );
    }
    
    /**
     * Handle route data from the chat
     */
    handleRouteData(data) {
        console.log('Route data received from chat:', data);
        
        // Store for reference
        this.pendingRouteData = data;
        
        // Render on map
        if (this.mapHandler && data.geojson) {
            this.mapHandler.renderRoute(data.geojson, data.metadata);
        }
        
        // Update route info panel
        this.updateRouteInfo(data.metadata);
        
        // Emit event for other listeners
        this.emit('routeReceived', data);
    }
    
    /**
     * Handle postMessage events (for iframe communication with Orchestrate)
     */
    handlePostMessage(event) {
        // Validate origin if needed
        // if (event.origin !== 'expected-origin') return;
        
        const data = event.data;
        
        // Check if this is route data from Orchestrate
        if (data && data.type === 'route_response') {
            this.handleRouteData(data.payload);
        }
        
        // Check for vibe extraction results
        if (data && data.type === 'vibe_extraction') {
            this.handleVibeExtraction(data.payload);
        }
    }
    
    /**
     * Handle extracted vibes from natural language
     */
    handleVibeExtraction(vibes) {
        console.log('Vibes extracted:', vibes);
        
        // Update UI sliders
        Object.entries(vibes).forEach(([key, value]) => {
            const slider = document.getElementById(key);
            if (slider) {
                slider.value = value * 100;
                const valueDisplay = document.getElementById(`${key}-value`);
                if (valueDisplay) {
                    valueDisplay.textContent = `${Math.round(value * 100)}%`;
                }
            }
        });
        
        this.emit('vibesExtracted', vibes);
    }
    
    /**
     * Update the route info panel
     */
    updateRouteInfo(metadata) {
        if (!metadata) return;
        
        const routeInfo = document.getElementById('route-info');
        if (routeInfo) {
            routeInfo.classList.remove('hidden');
        }
        
        // Update stats
        const distanceEl = document.getElementById('route-distance');
        if (distanceEl && metadata.distance_meters) {
            const km = (metadata.distance_meters / 1000).toFixed(1);
            distanceEl.textContent = `${km} km`;
        }
        
        const durationEl = document.getElementById('route-duration');
        if (durationEl && metadata.estimated_duration_minutes) {
            const mins = Math.round(metadata.estimated_duration_minutes);
            distanceEl.textContent = `${mins} min`;
        }
        
        const vibeScoreEl = document.getElementById('route-vibe-score');
        if (vibeScoreEl && metadata.vibe_score !== undefined) {
            vibeScoreEl.textContent = `${Math.round(metadata.vibe_score * 100)}%`;
        }
        
        // Update vibe breakdown
        const breakdownEl = document.getElementById('vibe-breakdown');
        if (breakdownEl && metadata.vibe_breakdown) {
            breakdownEl.innerHTML = Object.entries(metadata.vibe_breakdown)
                .filter(([key]) => key !== 'overall')
                .map(([key, value]) => `
                    <div class="vibe-breakdown-item">
                        <span>${this.formatVibeName(key)}</span>
                        <div class="vibe-breakdown-bar">
                            <div class="vibe-breakdown-fill" style="width: ${value * 100}%; background: ${CONFIG.VIBE_COLORS[key] || '#888'}"></div>
                        </div>
                        <span>${Math.round(value * 100)}%</span>
                    </div>
                `).join('');
        }
        
        // Update narrative
        const narrativeEl = document.getElementById('route-narrative');
        if (narrativeEl) {
            if (metadata.transparency_narrative) {
                narrativeEl.textContent = metadata.transparency_narrative;
                narrativeEl.style.display = 'block';
            } else {
                narrativeEl.style.display = 'none';
            }
        }
    }
    
    formatVibeName(key) {
        const names = {
            greenery: 'Greenery',
            blue_space: 'Blue Space',
            quietness: 'Quietness',
            liveliness: 'Liveliness',
            safety: 'Safety',
            walkability: 'Walkability'
        };
        return names[key] || key;
    }
    
    /**
     * Parse natural language to extract vibes
     * This is the fallback when Orchestrate isn't configured
     */
    parseNaturalLanguage(text) {
        const vibes = {
            greenery: 0.5,
            blue_space: 0,
            introvert_mode: 0,
            extrovert_mode: 0,
            safety_check: 0.5,
            walkability: 0.7
        };
        
        // Check each vibe pattern
        Object.entries(CONFIG.VIBE_PATTERNS).forEach(([vibe, patterns]) => {
            patterns.forEach((pattern) => {
                if (pattern.test(text)) {
                    // Boost this vibe
                    vibes[vibe] = Math.min(1, vibes[vibe] + 0.4);
                }
            });
        });
        
        // Extract duration
        let duration = 30;
        const minMatch = text.match(/(\d+)\s*(?:minute|min)/i);
        if (minMatch) {
            duration = parseInt(minMatch[1], 10);
        }
        const hourMatch = text.match(/(\d+)\s*(?:hour|hr)/i);
        if (hourMatch) {
            duration = parseInt(hourMatch[1], 10) * 60;
        }
        if (/half\s*(?:an?\s*)?hour/i.test(text)) {
            duration = 30;
        }
        if (/quick|short/i.test(text)) {
            duration = 15;
        }
        if (/long/i.test(text)) {
            duration = 60;
        }
        
        // Determine mode
        let mode = 'circular_loop';
        if (/to\s+\w+|from\s+\w+\s+to/i.test(text)) {
            mode = 'point_to_point';
        }
        
        return { vibes, duration, mode };
    }
    
    // Simple event emitter
    emit(event, data) {
        document.dispatchEvent(new CustomEvent(`orchestrate:${event}`, { detail: data }));
    }
    
    on(event, callback) {
        document.addEventListener(`orchestrate:${event}`, (e) => callback(e.detail));
    }
    
    destroy() {
        this.observers.forEach(obs => obs.disconnect());
        window.removeEventListener('message', this.handlePostMessage);
    }
}

// Export for use
window.OrchestrateBridge = OrchestrateBridge;
