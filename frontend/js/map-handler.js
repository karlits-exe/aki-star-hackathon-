/**
 * Map Handler - Manages Leaflet map and route rendering
 */
class MapHandler {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.markers = {
            start: null,
            end: null
        };
        this.routeLayer = null;
        this.clickMode = 'start'; // 'start', 'end', or null
        
        this.init();
    }
    
    init() {
        // Initialize map
        this.map = L.map(this.containerId).setView(
            [CONFIG.DEFAULT_CENTER.lat, CONFIG.DEFAULT_CENTER.lon],
            CONFIG.DEFAULT_ZOOM
        );
        
        // Add tile layer
        L.tileLayer(CONFIG.TILE_URL, {
            attribution: CONFIG.TILE_ATTRIBUTION,
            maxZoom: 19
        }).addTo(this.map);
        
        // Add click handler
        this.map.on('click', this.handleMapClick.bind(this));
        
        // Create route layer group
        this.routeLayer = L.layerGroup().addTo(this.map);
        
        console.log('Map initialized');
    }
    
    handleMapClick(e) {
        const { lat, lng } = e.latlng;
        
        if (this.clickMode === 'start') {
            this.setStartMarker(lat, lng);
            // Switch to end mode for point-to-point
            if (window.app && window.app.routeMode === 'point_to_point') {
                this.clickMode = 'end';
                this.updateClickHint('Now click to set your destination');
            }
        } else if (this.clickMode === 'end') {
            this.setEndMarker(lat, lng);
            this.clickMode = null;
            this.updateClickHint('');
        }
        
        // Trigger callback if set
        if (this.onMarkerSet) {
            this.onMarkerSet({
                start: this.getStartCoords(),
                end: this.getEndCoords()
            });
        }
    }
    
    setStartMarker(lat, lon) {
        // Remove existing start marker
        if (this.markers.start) {
            this.map.removeLayer(this.markers.start);
        }
        
        // Create custom icon
        const icon = L.divIcon({
            className: 'custom-marker start-marker',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });
        
        this.markers.start = L.marker([lat, lon], { icon })
            .addTo(this.map)
            .bindPopup('Start Point')
            .openPopup();
        
        // Send location context to Orchestrate if bridge is available
        if (window.app && window.app.orchestrateBridge) {
            window.app.orchestrateBridge.sendLocationContext(lat, lon, 'User Selected Location');
        }
        
        console.log(`Start marker set: ${lat}, ${lon}`);
    }
    
    setEndMarker(lat, lon) {
        if (this.markers.end) {
            this.map.removeLayer(this.markers.end);
        }
        
        const icon = L.divIcon({
            className: 'custom-marker end-marker',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });
        
        this.markers.end = L.marker([lat, lon], { icon })
            .addTo(this.map)
            .bindPopup('End Point');
        
        console.log(`End marker set: ${lat}, ${lon}`);
    }
    
    getStartCoords() {
        if (!this.markers.start) return null;
        const latlng = this.markers.start.getLatLng();
        return { lat: latlng.lat, lon: latlng.lng };
    }
    
    getEndCoords() {
        if (!this.markers.end) return null;
        const latlng = this.markers.end.getLatLng();
        return { lat: latlng.lat, lon: latlng.lng };
    }
    
    clearRoute() {
        this.routeLayer.clearLayers();
    }
    
    clearMarkers() {
        if (this.markers.start) {
            this.map.removeLayer(this.markers.start);
            this.markers.start = null;
        }
        if (this.markers.end) {
            this.map.removeLayer(this.markers.end);
            this.markers.end = null;
        }
    }
    
    renderRoute(geojson, metadata) {
        // Clear existing route
        this.clearRoute();
        
        // Determine route color
        const routeType = geojson.features[0]?.properties?.route_type || 'point_to_point';
        const color = CONFIG.ROUTE_COLORS[routeType] || CONFIG.ROUTE_COLORS.point_to_point;
        
        // Style function
        const style = {
            color: color,
            weight: 5,
            opacity: 0.8,
            lineCap: 'round',
            lineJoin: 'round'
        };
        
        // Add GeoJSON layer
        const routeGeoJSON = L.geoJSON(geojson, {
            style: style,
            onEachFeature: (feature, layer) => {
                // Add popup with route info
                const props = feature.properties || {};
                let popupContent = '<strong>Route</strong>';
                if (props.disjoint_percentage !== undefined) {
                    popupContent += `<br>Path variety: ${(props.disjoint_percentage * 100).toFixed(0)}%`;
                }
                layer.bindPopup(popupContent);
            }
        });
        
        this.routeLayer.addLayer(routeGeoJSON);
        
        // Fit map to route bounds
        const bounds = routeGeoJSON.getBounds();
        this.map.fitBounds(bounds, { padding: [50, 50] });
        
        console.log('Route rendered');
    }
    
    updateClickHint(message) {
        const hint = document.getElementById('click-hint');
        if (hint) {
            hint.textContent = message || 'Click on the map to set your starting point';
        }
    }
    
    setClickMode(mode) {
        this.clickMode = mode;
        if (mode === 'start') {
            this.updateClickHint('Click on the map to set your starting point');
        } else if (mode === 'end') {
            this.updateClickHint('Click on the map to set your destination');
        } else {
            this.updateClickHint('');
        }
    }
    
    async centerOnUserLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    this.map.setView([latitude, longitude], CONFIG.DEFAULT_ZOOM);
                    this.setStartMarker(latitude, longitude);
                    resolve({ lat: latitude, lon: longitude });
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    reject(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 60000
                }
            );
        });
    }
}

// Export for use
window.MapHandler = MapHandler;
