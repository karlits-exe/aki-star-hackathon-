# Unnamed - Generative Walking Route Planner

> Walk by Vibes, Not by Speed

A vibe-based walking route planner built for the **IBM Dev Day "AI Demystified" Hackathon**. This project "demystifies" complex routing algorithms by letting users describe their ideal walk in natural language, then transparently explaining why each route was chosen.

## The Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID AGENTIC ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │   THE FACE   │───▶│    THE BRAIN     │───▶│  THE MUSCLE  │  │
│  │  (Frontend)  │    │ (IBM watsonx     │    │   (Python    │  │
│  │  HTML/JS/CSS │◀───│   Orchestrate)   │◀───│   Backend)   │  │
│  └──────────────┘    └──────────────────┘    └──────────────┘  │
│         │                     │                      │          │
│         │              Intent & NLU          Graph Algorithms   │
│         │              Demystification       Dijkstra / A*      │
│         │                                                       │
│         └─────────────────────┬─────────────────────────────────┘
│                               │                                  │
│                               ▼                                  │
│                    ┌──────────────────┐                         │
│                    │  OpenStreetMap   │                         │
│                    │   (ODbL Data)    │                         │
│                    └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Natural Language Routing**: Describe your ideal walk - "I want a peaceful nature walk" or "Plan a safe evening stroll"
- **Vibe-Based Optimization**: Routes optimized for:
  - Greenery (parks, trees, gardens)
  - Blue Space (rivers, lakes, coastline)
  - Introvert Mode (quiet, peaceful areas)
  - Extrovert Mode (lively, bustling streets)
  - Safety Check (well-lit streets)
  - Walkability (pedestrian-friendly paths)
- **Circular Loops**: Generate round-trip walks with disjoint return paths
- **Transparency**: AI explains why each route was chosen
- **No-Go Zones**: Avoid specific areas

## The Generative Cost Function

The core algorithm uses a custom cost function:

```
Cg = C_base × (1 - Quality_Score)
```

Where:
- `C_base` = Original edge distance/time
- `Quality_Score` = How well the edge matches user vibes (0-1)
- Result: High-quality edges get lower costs (preferred by pathfinding)

**Magnets** (attractors) reduce cost:
- Parks → Greenery
- Rivers → Blue Space
- Shops/Cafes → Liveliness
- Lit streets → Safety

**Repellents** (detractors) increase cost:
- Highways → Quietness
- Industrial areas → Greenery
- Unlit streets → Safety

## Quick Start

### Prerequisites
- Python 3.10+
- ngrok (for exposing local backend)
- IBM Cloud account (for watsonx Orchestrate)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create environment file
cp ../.env.example .env
# Edit .env with your IBM credentials (optional)

# Run the server
python main.py
```

### 2. Expose with ngrok

```bash
ngrok http 8000
# Copy the HTTPS URL
```

### 3. Update Frontend Config

Edit `frontend/js/config.js`:
```javascript
API_BASE_URL: 'https://your-ngrok-url.ngrok.io'
```

### 4. Open Frontend

Open `frontend/index.html` in your browser, or serve it:
```bash
cd frontend
python -m http.server 3000
```

### 5. Configure watsonx Orchestrate

See [docs/ORCHESTRATE_SETUP.md](docs/ORCHESTRATE_SETUP.md) for detailed instructions.

## Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Environment configuration
│   ├── models/                 # Pydantic schemas
│   │   ├── request_models.py   # API request schemas
│   │   └── response_models.py  # GeoJSON response schemas
│   └── services/
│       ├── graph_loader.py     # OSMnx graph management
│       ├── cost_functions.py   # Generative cost function
│       ├── vibe_engine.py      # Magnet/Repellent system
│       ├── routing.py          # Dijkstra/A* implementation
│       └── loop_generator.py   # Circular route generation
│
├── frontend/
│   ├── index.html              # Main page
│   ├── styles.css              # Styling
│   └── js/
│       ├── config.js           # Configuration
│       ├── map-handler.js      # Leaflet map management
│       ├── orchestrate-bridge.js # Chat-to-map handshake
│       └── script.js           # Main application logic
│
├── openapi/
│   ├── openapi.yaml            # OpenAPI 3.0 specification
│   └── orchestrate-skill.json  # Orchestrate skill definition
│
└── docs/
    ├── ORCHESTRATE_SETUP.md    # Orchestrate configuration guide
    └── DEPLOYMENT.md           # Deployment instructions
```

## API Endpoints

### POST /route
Generate a walking route.

```json
{
  "mode": "circular_loop",
  "origin": {"lat": 14.5547, "lon": 121.0244},
  "duration_minutes": 30,
  "vibes": {
    "greenery": 0.9,
    "safety_check": 0.8
  }
}
```

### GET /health
Health check endpoint.

## Hackathon Compliance

| Requirement | Status |
|------------|--------|
| Data from public websites | OpenStreetMap (ODbL) |
| No restricted models | Uses Granite / Llama 3.2 only |
| Credentials secured | .env files gitignored |
| Demystifies AI | Transparency narratives explain routing |

## Technology Stack

- **Backend**: Python, FastAPI, OSMnx, NetworkX
- **Frontend**: HTML, CSS, JavaScript, Leaflet
- **AI/ML**: IBM watsonx Orchestrate, Granite models
- **Data**: OpenStreetMap

## Team

Built for IBM Dev Day "AI Demystified" Hackathon

## License

MIT License - See LICENSE file

---

*Walk by vibes, not by speed.*
