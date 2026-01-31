# Deployment Guide

This guide covers deploying the Walking Route Planner for the IBM Hackathon.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│  watsonx         │────▶│  Backend API    │
│   (Browser)     │     │  Orchestrate     │     │  (FastAPI)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                                               │
        │                                               ▼
        │                                        ┌─────────────────┐
        └───────────────────────────────────────▶│  OpenStreetMap  │
                  (Direct API calls)             │  (OSM Data)     │
                                                 └─────────────────┘
```

## Option 1: Local Development with ngrok (Recommended for Hackathon)

### Prerequisites
- Python 3.10+
- ngrok account (free tier works)
- Node.js (optional, for serving frontend)

### Step 1: Set Up Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env
# Edit .env with your IBM credentials (optional for narrative generation)

# Run the backend
python main.py
# Or with uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Expose with ngrok

```bash
# In a new terminal
ngrok http 8000

# You'll see output like:
# Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

**Important**: Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

### Step 3: Update Frontend Config

Edit `frontend/js/config.js`:
```javascript
const CONFIG = {
    API_BASE_URL: 'https://abc123.ngrok.io',  // Your ngrok URL
    // ...
};
```

### Step 4: Serve Frontend

Option A - Using Python:
```bash
cd frontend
python -m http.server 3000
```

Option B - Using Node.js:
```bash
npx serve frontend -p 3000
```

Option C - Open directly in browser:
- Just open `frontend/index.html` in your browser

### Step 5: Update Orchestrate

1. Go to watsonx Orchestrate
2. Update the skill's server URL to your ngrok URL
3. Test the integration

## Option 2: Deploy to Render (Free Tier)

### Step 1: Prepare for Deployment

Create `render.yaml` in project root:
```yaml
services:
  - type: web
    name: walking-route-api
    env: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: WATSONX_API_KEY
        sync: false
      - key: WATSONX_PROJECT_ID
        sync: false
```

### Step 2: Deploy Backend

1. Push code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** > **Web Service**
4. Connect your GitHub repo
5. Configure:
   - Name: `walking-route-api`
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables (if using watsonx for narratives)
7. Deploy

### Step 3: Deploy Frontend

Option A - Render Static Site:
1. Create new **Static Site** on Render
2. Root Directory: `frontend`
3. Publish Directory: `.`

Option B - GitHub Pages:
1. Go to repo Settings > Pages
2. Select branch and `/frontend` folder
3. Save

Option C - Vercel:
```bash
cd frontend
npx vercel
```

## Option 3: Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

## Environment Variables

### Backend (.env)
```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# IBM watsonx (optional - for AI narratives)
WATSONX_API_KEY=your-api-key-here
WATSONX_PROJECT_ID=your-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-13b-chat-v2

# Graph caching
CACHE_DIR=./data/cache

# Default location (Metro Manila)
DEFAULT_LAT=14.5547
DEFAULT_LON=121.0244
DEFAULT_PLACE=Makati, Metro Manila, Philippines
```

### Frontend (config.js)
```javascript
API_BASE_URL: 'https://your-deployed-url.com'
```

## CORS Configuration

The backend is configured to allow all origins for development:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, restrict to your frontend domain:
```python
allow_origins=["https://your-frontend-domain.com"]
```

## Testing the Deployment

### 1. Health Check
```bash
curl https://your-api-url.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "graph_loaded": true,
  "cached_regions": ["makati"]
}
```

### 2. Test Route Generation
```bash
curl -X POST https://your-api-url.com/route \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "circular_loop",
    "origin": {"lat": 14.5547, "lon": 121.0244},
    "duration_minutes": 30,
    "vibes": {"greenery": 0.8, "safety_check": 0.7}
  }'
```

### 3. Test Frontend
1. Open the frontend URL in browser
2. Click on the map to set a starting point
3. Adjust vibes and click "Generate Route"
4. Verify route appears on map

## Troubleshooting

### Backend won't start
- Check Python version (3.10+ required)
- Verify all dependencies installed
- Check port isn't already in use

### OSM graph download fails
- First download can take 2-5 minutes
- Check internet connection
- Try a smaller area first

### CORS errors
- Verify backend CORS settings
- Check ngrok URL matches config
- Try disabling browser CORS extensions

### Orchestrate can't reach backend
- Verify ngrok is running
- Check ngrok URL hasn't changed
- Test backend directly with curl

## Performance Tips

1. **Pre-cache OSM data**: Run the backend once to cache the graph
2. **Use smaller regions**: Start with a specific city area, not entire cities
3. **Increase timeout**: For first requests, graph download may be slow

## Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] No API keys in frontend code
- [ ] CORS restricted in production
- [ ] HTTPS used for all communications
