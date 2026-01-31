"""
Generative Walking Route Planner - FastAPI Backend

Main entry point for the routing API.
Provides endpoints for point-to-point and circular loop routing.

Data Source: OpenStreetMap (OSM) under ODbL license.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import httpx
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
from services.graph_loader import GraphLoader
from services.cost_functions import CostFunctionEngine
from services.vibe_engine import VibeEngine
from services.routing import RoutingService
from services.loop_generator import LoopGenerator

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global graph_loader, cost_engine, vibe_engine, routing_service, loop_generator
    
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
    A vibe-based walking route planner that generates routes based on user preferences.
    
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


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API health and graph status."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        graph_loaded=graph_loader is not None and graph_loader.graph is not None,
        cached_regions=graph_loader.list_cached_regions() if graph_loader else []
    )


@app.post(
    "/route",
    response_model=RouteResponse,
    tags=["Routing"],
    summary="Generate a walking route",
    description="""
    Generate a walking route based on vibes and preferences.
    
    Supports two modes:
    - **point_to_point**: Route from origin to destination
    - **circular_loop**: Round-trip from origin back to origin
    
    ## Vibe Parameters
    All vibes are floats from 0.0 to 1.0:
    - **greenery**: Prefer parks and green spaces
    - **blue_space**: Prefer water features (rivers, lakes)
    - **introvert_mode**: Prefer quiet, peaceful areas
    - **extrovert_mode**: Prefer lively, bustling areas
    - **safety_check**: Prefer well-lit, safe streets
    - **walkability**: Prefer pedestrian-friendly paths
    """
)
async def generate_route(request: RouteRequest) -> RouteResponse:
    """Generate a walking route."""
    global graph_loader, cost_engine, vibe_engine, routing_service, loop_generator
    
    # Validate request
    if request.mode == RouteMode.POINT_TO_POINT and request.destination is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination is required for point_to_point mode"
        )
    
    try:
        # Ensure graph is loaded for the region
        if graph_loader is None or graph_loader.graph is None:
            graph_loader = GraphLoader(settings.cache_dir)
            # Load graph around origin point
            graph = graph_loader.load_graph_by_point(
                request.origin.lat,
                request.origin.lon,
                dist_meters=3000
            )
            cost_engine = CostFunctionEngine(graph_loader.amenities)
            vibe_engine = VibeEngine(graph_loader.amenities)
            routing_service = RoutingService(graph, cost_engine, vibe_engine)
            loop_generator = LoopGenerator(graph, routing_service, cost_engine, vibe_engine)
        
        # Get nearest nodes
        origin_node = graph_loader.get_nearest_node(
            request.origin.lat,
            request.origin.lon
        )
        
        # Convert vibe weights to dict
        vibe_weights = request.vibes.model_dump()
        
        # Add no-go zones to vibe engine
        for zone in request.no_go_zones:
            # Calculate zone centroid
            center_lat = sum(v.lat for v in zone.vertices) / len(zone.vertices)
            center_lon = sum(v.lon for v in zone.vertices) / len(zone.vertices)
            vibe_engine.add_no_go_zone(center_lat, center_lon, radius_meters=150)
        
        if request.mode == RouteMode.CIRCULAR_LOOP:
            # Generate circular loop
            result = loop_generator.generate_loop_bidirectional(
                origin_node,
                request.duration_minutes,
                vibe_weights
            )
            
            # Build GeoJSON
            coords = [[lon, lat] for lat, lon in result.full_path_coords]
            
            geojson = GeoJSONFeatureCollection(
                features=[
                    GeoJSONFeature(
                        geometry=GeoJSONGeometry(coordinates=coords),
                        properties={
                            "stroke": "#22c55e",
                            "stroke-width": 4,
                            "stroke-opacity": 0.8,
                            "route_type": "circular_loop",
                            "disjoint_percentage": result.disjoint_percentage
                        }
                    )
                ]
            )
            
            # Generate narrative if requested
            narrative = None
            if request.include_narrative:
                narrative = vibe_engine.generate_transparency_summary(
                    result.vibe_profile,
                    vibe_weights
                )
                # Optionally enhance with watsonx
                if settings.watsonx_api_key:
                    narrative = await _generate_ai_narrative(
                        result.vibe_profile,
                        vibe_weights,
                        result.total_distance,
                        result.total_time
                    )
            
            return RouteResponse(
                success=True,
                geojson=geojson,
                metadata=RouteMetadata(
                    distance_meters=result.total_distance,
                    estimated_duration_minutes=result.total_time / 60,
                    vibe_score=result.vibe_profile.overall,
                    vibe_breakdown=result.vibe_profile.to_dict(),
                    transparency_narrative=narrative,
                    algorithm_used="bidirectional_astar",
                    nodes_explored=result.nodes_explored
                )
            )
        
        else:
            # Point-to-point routing
            dest_node = graph_loader.get_nearest_node(
                request.destination.lat,
                request.destination.lon
            )
            
            result = routing_service.find_route(
                origin_node,
                dest_node,
                vibe_weights,
                algorithm="astar"
            )
            
            # Build GeoJSON
            coords = [[lon, lat] for lat, lon in result.path_coords]
            
            geojson = GeoJSONFeatureCollection(
                features=[
                    GeoJSONFeature(
                        geometry=GeoJSONGeometry(coordinates=coords),
                        properties={
                            "stroke": "#3b82f6",
                            "stroke-width": 4,
                            "stroke-opacity": 0.8,
                            "route_type": "point_to_point"
                        }
                    )
                ]
            )
            
            # Generate narrative
            narrative = None
            if request.include_narrative:
                narrative = vibe_engine.generate_transparency_summary(
                    result.vibe_profile,
                    vibe_weights
                )
                if settings.watsonx_api_key:
                    narrative = await _generate_ai_narrative(
                        result.vibe_profile,
                        vibe_weights,
                        result.total_distance,
                        result.total_time
                    )
            
            return RouteResponse(
                success=True,
                geojson=geojson,
                metadata=RouteMetadata(
                    distance_meters=result.total_distance,
                    estimated_duration_minutes=result.total_time / 60,
                    vibe_score=result.vibe_profile.overall,
                    vibe_breakdown=result.vibe_profile.to_dict(),
                    transparency_narrative=narrative,
                    algorithm_used=result.algorithm,
                    nodes_explored=result.nodes_explored
                )
            )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Error generating route")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route generation failed: {str(e)}"
        )


async def _generate_ai_narrative(
    vibe_profile,
    vibe_weights: dict,
    distance: float,
    time: float
) -> str:
    """
    Generate AI narrative using IBM watsonx Granite model.
    
    This enhances the transparency narrative with AI-generated explanations.
    """
    if not settings.watsonx_api_key:
        return None
    
    try:
        # Build prompt
        prompt = f"""You are a helpful walking route assistant. Explain why this route was chosen in 2-3 sentences.

Route details:
- Distance: {distance:.0f} meters ({distance/1000:.1f} km)
- Estimated time: {time/60:.0f} minutes
- Vibe scores achieved:
  - Greenery: {vibe_profile.greenery:.0%}
  - Safety: {vibe_profile.safety:.0%}
  - Quietness: {vibe_profile.quietness:.0%}
  - Walkability: {vibe_profile.walkability:.0%}

User preferences:
- Greenery importance: {vibe_weights.get('greenery', 0):.0%}
- Safety importance: {vibe_weights.get('safety_check', 0):.0%}
- Quiet areas importance: {vibe_weights.get('introvert_mode', 0):.0%}
- Walkability importance: {vibe_weights.get('walkability', 0):.0%}

Explain the route choice briefly and naturally:"""

        # Call watsonx API
        async with httpx.AsyncClient() as client:
            # Get IAM token
            token_response = await client.post(
                "https://iam.cloud.ibm.com/identity/token",
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": settings.watsonx_api_key
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token = token_response.json().get("access_token")
            
            # Call model
            response = await client.post(
                f"{settings.watsonx_url}/ml/v1/text/generation?version=2024-01-01",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model_id": settings.watsonx_model_id,
                    "project_id": settings.watsonx_project_id,
                    "input": prompt,
                    "parameters": {
                        "max_new_tokens": 150,
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=30.0
            )
            
            result = response.json()
            return result.get("results", [{}])[0].get("generated_text", "").strip()
    
    except Exception as e:
        logger.warning(f"AI narrative generation failed: {e}")
        return None


@app.get("/cached-regions", tags=["System"])
async def list_cached_regions():
    """List all cached graph regions."""
    if graph_loader is None:
        return {"regions": []}
    return {"regions": graph_loader.list_cached_regions()}


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
