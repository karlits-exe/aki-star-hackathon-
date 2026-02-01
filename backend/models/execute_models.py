"""
Execute models for clean, parameter-only route execution.

These models are designed for the /execute endpoint which receives
clean parameters from watsonx Orchestrate and executes the routing
algorithm without any strategic decision-making.
"""
from pydantic import BaseModel, Field
from typing import Any, Optional


class Coordinate(BaseModel):
    """A geographic coordinate point."""
    lat: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in decimal degrees (-90 to 90)"
    )
    lon: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in decimal degrees (-180 to 180)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {"lat": 14.5547, "lon": 121.0244}
        }


class VibeWeights(BaseModel):
    """
    Precise vibe weights as floats from 0.0 to 1.0.
    
    These are set by Orchestrate based on strategic analysis
    of the user's natural language request.
    """
    greenery: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Preference for parks, trees, green spaces (0-1)"
    )
    blue_space: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Preference for water bodies, rivers, lakes (0-1)"
    )
    introvert_mode: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Preference for quiet, peaceful areas (0-1)"
    )
    extrovert_mode: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Preference for lively, bustling areas (0-1)"
    )
    safety_check: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Preference for well-lit, safe streets (0-1)"
    )
    walkability: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Preference for pedestrian-friendly paths (0-1)"
    )


class NoGoZone(BaseModel):
    """A polygon area to avoid during routing."""
    vertices: list[Coordinate] = Field(
        ...,
        min_length=3,
        description="List of coordinates forming a closed polygon (minimum 3 points)"
    )


class ExecuteRequest(BaseModel):
    """
    Clean execution request from watsonx Orchestrate.
    
    This model contains only the parameters needed to execute
    the routing algorithm - no strategic logic, no natural language.
    All strategic decisions (algorithm selection, vibe balancing, etc.)
    have already been made by Orchestrate.
    """
    origin: Optional[Coordinate] = Field(
        default=None,
        description="Starting point coordinates (provided by frontend context or user). If not provided, session_id must be provided."
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID to retrieve location from frontend. Use this when origin is not provided."
    )
    duration_minutes: int = Field(
        default=30,
        ge=5,
        le=180,
        description="Target walk duration in minutes. Always generates circular loop."
    )
    vibes: VibeWeights = Field(
        default_factory=VibeWeights,
        description="Precise vibe weights (0-1) strategically set by Orchestrate based on user intent"
    )
    no_go_zones: list[NoGoZone] = Field(
        default_factory=list,
        description="Polygon areas to avoid during routing"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "High greenery request",
                    "value": {
                        "origin": {"lat": 14.5547, "lon": 121.0244},
                        "duration_minutes": 45,
                        "vibes": {
                            "greenery": 0.9,
                            "introvert_mode": 0.7,
                            "safety_check": 0.6,
                            "walkability": 0.8
                        }
                    }
                },
                {
                    "summary": "Safe evening walk",
                    "value": {
                        "origin": {"lat": 14.5547, "lon": 121.0244},
                        "duration_minutes": 30,
                        "vibes": {
                            "safety_check": 0.95,
                            "walkability": 0.9,
                            "greenery": 0.4
                        }
                    }
                }
            ]
        }


class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry object."""
    type: str = Field(default="LineString")
    coordinates: list[list[float]] = Field(
        ...,
        description="Array of [longitude, latitude] coordinate pairs"
    )


class GeoJSONFeature(BaseModel):
    """GeoJSON feature object."""
    type: str = Field(default="Feature")
    geometry: GeoJSONGeometry
    properties: dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection for map rendering."""
    type: str = Field(default="FeatureCollection")
    features: list[GeoJSONFeature]


class VibeBreakdown(BaseModel):
    """Detailed vibe scores for transparency."""
    greenery: float
    blue_space: float
    quietness: float
    liveliness: float
    safety: float
    walkability: float
    overall: float


class RouteMetadata(BaseModel):
    """Route metadata for display."""
    distance_meters: float = Field(..., description="Total route distance in meters")
    estimated_duration_minutes: float = Field(..., description="Estimated walking time in minutes")
    vibe_score: float = Field(..., ge=0.0, le=1.0, description="Overall route quality based on vibes")
    vibe_breakdown: VibeBreakdown = Field(..., description="Individual vibe scores achieved")


class ExecutionDetails(BaseModel):
    """
    Technical execution details for demystification.
    
    These details show HOW the route was generated,
    satisfying the "AI Demystified" theme.
    """
    algorithm: str = Field(default="dijkstra", description="Pathfinding algorithm used")
    nodes_explored: int = Field(..., description="Number of graph nodes explored")
    graph_size: str = Field(..., description="Size of OSM graph (nodes/edges)")
    disjoint_percentage: float = Field(
        ...,
        description="Percentage of return path that is unique (0-1)"
    )
    execution_time_ms: float = Field(
        ...,
        description="Time taken to generate route in milliseconds"
    )


class ExecuteResponse(BaseModel):
    """
    Clean execution response.
    
    Contains the route result plus technical details
    for Orchestrate to use in its explanation.
    """
    success: bool = Field(default=True)
    geojson: GeoJSONFeatureCollection = Field(
        ...,
        description="GeoJSON FeatureCollection for map rendering"
    )
    metadata: RouteMetadata = Field(
        ...,
        description="Route statistics and vibe scores"
    )
    execution_details: ExecutionDetails = Field(
        ...,
        description="Technical details showing how the route was generated"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[121.0244, 14.5547], [121.0250, 14.5550]]
                        },
                        "properties": {
                            "stroke": "#22c55e",
                            "stroke-width": 4
                        }
                    }]
                },
                "metadata": {
                    "distance_meters": 2450.5,
                    "estimated_duration_minutes": 32.7,
                    "vibe_score": 0.78,
                    "vibe_breakdown": {
                        "greenery": 0.85,
                        "blue_space": 0.2,
                        "quietness": 0.72,
                        "liveliness": 0.15,
                        "safety": 0.80,
                        "walkability": 0.85,
                        "overall": 0.78
                    }
                },
                "execution_details": {
                    "algorithm": "dijkstra",
                    "nodes_explored": 342,
                    "graph_size": "5,590 nodes, 15,954 edges",
                    "disjoint_percentage": 0.73,
                    "execution_time_ms": 125
                }
            }
        }


class ExecuteErrorResponse(BaseModel):
    """Error response for failed execution."""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message for Orchestrate to display")
    error_code: str = Field(..., description="Machine-readable error code")
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for the user to try different parameters"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Could not generate route with specified constraints",
                "error_code": "NO_VALID_PATH",
                "suggestions": [
                    "Try a shorter duration (e.g., 20 minutes instead of 60)",
                    "Reduce vibe constraints (e.g., lower greenery requirement)",
                    "Select a different starting location with more walking paths"
                ]
            }
        }
