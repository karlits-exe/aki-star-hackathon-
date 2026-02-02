const CONFIG = {
    // Backend API URL (update this when using ngrok)
    API_BASE_URL: 'https://638be3913b41.ngrok-free.app',

    // IBM Cloud API Key for watsonx Orchestrate authentication
    // NOTE: In production, this should be fetched from your backend, not exposed in frontend code
    // Set via environment variable: process.env.IBM_CLOUD_API_KEY or similar
    IBM_CLOUD_API_KEY: '',

    // Session ID for location sharing with backend
    SESSION_ID: 'session_' + Math.random().toString(36).substring(2, 15),

    // Default map center (Makati, Metro Manila - best OSM data in Philippines)
    DEFAULT_CENTER: {
        lat: 14.5547,
        lon: 121.0244
    },

    // Default zoom level
    DEFAULT_ZOOM: 15,

    // Map tile provider (OpenStreetMap)
    TILE_URL: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    TILE_ATTRIBUTION: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',

    // Route colors
    ROUTE_COLORS: {
        circular_loop: '#22c55e',  // Green for loops
        point_to_point: '#3b82f6', // Blue for point-to-point
        outbound: '#22c55e',
        return: '#f59e0b'
    },

    // Vibe colors for visualization
    VIBE_COLORS: {
        greenery: '#22c55e',
        blue_space: '#3b82f6',
        quietness: '#8b5cf6',
        liveliness: '#f59e0b',
        safety: '#eab308',
        walkability: '#06b6d4'
    },

    // Natural language patterns for chat parsing
    VIBE_PATTERNS: {
        greenery: [
            /nature/i, /green/i, /park/i, /tree/i, /garden/i, /scenic/i, /forest/i
        ],
        blue_space: [
            /water/i, /river/i, /lake/i, /beach/i, /coast/i, /sea/i
        ],
        introvert_mode: [
            /quiet/i, /peaceful/i, /calm/i, /serene/i, /alone/i, /solitude/i, /avoid.+crowd/i
        ],
        extrovert_mode: [
            /lively/i, /bustling/i, /busy/i, /vibrant/i, /exciting/i, /shops/i, /cafe/i
        ],
        safety_check: [
            /safe/i, /secure/i, /well.?lit/i, /evening/i, /night/i, /bright/i
        ],
        walkability: [
            /easy/i, /pedestrian/i, /sidewalk/i, /flat/i, /accessible/i
        ]
    },

    // Duration patterns for parsing
    DURATION_PATTERNS: [
        /(\d+)\s*(?:minute|min)/i,
        /(\d+)\s*(?:hour|hr)/i,
        /half\s*(?:an?\s*)?hour/i,
        /quick/i,
        /short/i,
        /long/i
    ]
};

// Make config available globally
window.APP_CONFIG = CONFIG;
