"""
Generative Walking Route Planner - FastAPI Backend

Main entry point for the routing API.
Provides endpoints for point-to-point and circular loop routing.

Data Source: OpenStreetMap (OSM) under ODbL license.
"""
from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import httpx
import time
import json
from typing import Optional

from config import get_settings
from models import (
    RouteRequest,
    RouteResponse,
    RouteMetadata,
    ErrorResponse,
    HealthResponse,
    RouteMode,
)
from models.response_models import (
    GeoJSONFeatureCollection,
    GeoJSONFeature,
    GeoJSONGeometry,
)
from models.execute_models import (
    ExecuteRequest,
    ExecuteResponse,
    ExecuteErrorResponse,
    Coordinate
)
from services.graph_loader import GraphLoader
from services.cost_functions import CostFunctionEngine
from services.vibe_engine import VibeEngine
from services.routing import RoutingService
from services.loop_generator import LoopGenerator
from services.execution_service import ExecutionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
settings = get_settings()
graph_loader: Optional[GraphLoader] = None
cost_engine: Optional[CostFunctionEngine] = None
vibe_engine: Optional[VibeEngine] = None
routing_service: Optional[RoutingService] = None
loop_generator: Optional[LoopGenerator] = None
execution_service: Optional[ExecutionService] = None

# Simple session storage for location context
location_sessions: dict[str, dict] = {}
route_results: dict[str, dict] = {}  # Store route results by session_id

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time route updates."""
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_route(self, session_id: str, route_data: dict):
        """Send route data to specific session."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json({
                    "type": "route_ready",
                    "data": route_data
                })
                logger.info(f"Route sent via WebSocket to session {session_id}")
            except Exception as e:
                logger.error(f"Failed to send route via WebSocket: {e}")

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global graph_loader, cost_engine, vibe_engine, routing_service, loop_generator, execution_service
    
    logger.info("Starting Generative Walking Route Planner...")
    logger.info(f"Default location: {settings.default_place}")
    
    # Initialize graph loader
    graph_loader = GraphLoader(settings.cache_dir)
    
    # Pre-load default region graph
    try:
        logger.info(f"Loading graph for {settings.default_place}...")
        graph = graph_loader.load_graph_by_place(settings.default_place)
        logger.info(f"Graph loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        # Initialize engines
        cost_engine = CostFunctionEngine(graph_loader.amenities)
        vibe_engine = VibeEngine(graph_loader.amenities)
        routing_service = RoutingService(graph, cost_engine, vibe_engine)
        loop_generator = LoopGenerator(graph, routing_service, cost_engine, vibe_engine)
        execution_service = ExecutionService(graph_loader, graph)
        
        logger.info("All services initialized successfully!")
    except Exception as e:
        logger.warning(f"Could not pre-load graph: {e}")
        logger.info("Graph will be loaded on first request.")
    
    yield
    
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Generative Walking Route Planner API",
    description="""
    A vibe-based walking route planner API for the IBM Dev Day "AI Demystified" Hackathon.
    
    ## Features
    - **Point-to-Point Routing**: Find the best walking route between two points
    - **Circular Loops**: Generate round-trip walks of specified duration
    - **Vibe-Based Optimization**: Routes optimized for greenery, safety, quietness, etc.
    
    ## Data Source
    Route data from OpenStreetMap (OSM) under ODbL license.
    
    ## Hackathon Project
    Built for IBM Dev Day "AI Demystified" Hackathon.
    """,
    version="1.0.0",
    lifespan=lifespan,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket endpoint for real-time route updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for receiving route updates in real-time.
    Frontend connects here to get instant route when ready.
    """
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive, wait for messages (optional)
            data = await websocket.receive_text()
            # Can handle ping/pong or other messages here
    except WebSocketDisconnect:
        manager.disconnect(session_id)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API health and graph status."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        graph_loaded=graph_loader is not None and graph_loader.graph is not None,
        cached_regions=graph_loader.list_cached_regions() if graph_loader else []
    )


@app.get("/cached-regions", tags=["System"])
async def list_cached_regions():
    """List all cached graph regions."""
    if graph_loader is None:
        return {"regions": []}
    return {"regions": graph_loader.list_cached_regions()}


@app.post("/set-location", tags=["Session Management"])
async def set_location(request: dict):
    """
    Store location in session for later use by /execute.
    Called by frontend when user clicks on map.
    
    Expected JSON body:
    {
        "session_id": "session_abc123",
        "lat": 14.5547,
        "lon": 121.0244
    }
    """
    global location_sessions
    
    session_id = request.get("session_id")
    lat = request.get("lat")
    lon = request.get("lon")
    
    if not session_id or lat is None or lon is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: session_id, lat, lon"
        )
    
    location_sessions[session_id] = {
        "lat": lat,
        "lon": lon,
        "timestamp": time.time()
    }
    logger.info(f"Location stored for session {session_id}: {lat}, {lon}")
    return {"success": True, "message": "Location stored"}


@app.post(
    "/execute",
    response_model=ExecuteResponse,
    responses={400: {"model": ExecuteErrorResponse}},
    tags=["Orchestrate Integration"],
    summary="Execute route generation (Orchestrate entry point)",
    description="""
    Pure execution endpoint for watsonx Orchestrate.
    
    This endpoint receives clean execution parameters from Orchestrate
    and performs the routing algorithm without any strategic decisions.
    
    All strategic analysis (vibe mapping, algorithm selection, etc.)
    is done by Orchestrate before calling this endpoint.
    
    Always generates circular loop walks.
    """
)
async def execute_route(request: ExecuteRequest) -> ExecuteResponse:
    """
    Execute route generation with clean parameters from Orchestrate.
    """
    global graph_loader, execution_service, location_sessions, route_results
    
    try:
        # Handle location from session if origin not provided
        origin = request.origin
        if origin is None and request.session_id:
            session_data = location_sessions.get(request.session_id)
            if session_data:
                origin = Coordinate(lat=session_data["lat"], lon=session_data["lon"])
                logger.info(f"Retrieved location from session {request.session_id}: {origin.lat}, {origin.lon}")
            else:
                raise ValueError(f"Session {request.session_id} not found. Please select a location on the map first.")
        
        if origin is None:
            raise ValueError("Either origin coordinates or session_id must be provided")
        
        # Ensure graph is loaded and covers the user's location with walking network
        graph = None
        if graph_loader is None or graph_loader.graph is None:
            logger.info(f"Initializing graph loader for location ({origin.lat}, {origin.lon})")
            graph_loader = GraphLoader(settings.cache_dir)
            graph = graph_loader.load_graph_by_point(
                origin.lat,
                origin.lon,
                dist_meters=5000  # Increased from 3000 to capture more walking network
            )
        elif not graph_loader.is_point_in_graph_bounds(origin.lat, origin.lon, buffer_meters=1000):
            # User's location is outside the current graph bounds - reload graph centered on user
            logger.info(f"User location ({origin.lat}, {origin.lon}) outside current graph bounds. Reloading graph...")
            graph = graph_loader.load_graph_by_point(
                origin.lat,
                origin.lon,
                dist_meters=5000  # Increased from 3000
            )
        else:
            graph = graph_loader.graph
            logger.info(f"Using existing graph for location ({origin.lat}, {origin.lon})")
        
        # Ensure execution_service is initialized with the correct graph
        if execution_service is None or execution_service.graph is None or execution_service.graph != graph:
            if graph is None:
                logger.info(f"Graph is None, loading for location ({origin.lat}, {origin.lon})")
                graph_loader = GraphLoader(settings.cache_dir)
                graph = graph_loader.load_graph_by_point(
                    origin.lat,
                    origin.lon,
                    dist_meters=3000
                )
            logger.info(f"Creating new ExecutionService with graph at location ({origin.lat}, {origin.lon})")
            execution_service = ExecutionService(graph_loader, graph)
        
        # Create request with resolved origin
        execute_request = ExecuteRequest(
            origin=origin,
            duration_minutes=request.duration_minutes,
            vibes=request.vibes,
            no_go_zones=request.no_go_zones
        )
        
        # Execute the route
        result = execution_service.execute(execute_request)
        
        # Store route by session_id if provided (for frontend retrieval)
        if request.session_id:
            route_results[request.session_id] = result.model_dump()
            logger.info(f"Route stored for session {request.session_id}")
            
            # Send via WebSocket for real-time update
            await manager.send_route(request.session_id, result.model_dump())
        
        return result
        
    except ValueError as e:
        logger.error(f"Route execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Unexpected error during route execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route generation failed: {str(e)}"
        )


@app.get("/get-route/{session_id}", tags=["Session Management"])
async def get_route(session_id: str):
    """
    Retrieve a generated route by session ID.
    Called by frontend after user chats with Orchestrate.
    """
    global route_results
    
    route_data = route_results.get(session_id)
    if route_data:
        return route_data
    else:
        raise HTTPException(
            status_code=404,
            detail="No route found for this session. Please chat with the AI first to generate a route."
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
