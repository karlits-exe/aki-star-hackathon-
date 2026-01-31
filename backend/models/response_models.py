"""
Response models for the Generative Walking Route Planner API.

GeoJSON-compliant responses that can be directly rendered on Leaflet/Mapbox.
"""
from pydantic import BaseModel, Field
from typing import Any, Optional


class RouteMetadata(BaseModel):
    """Metadata about the generated route."""
    distance_meters: float = Field(
        ...,
        description="Total route distance in meters"
    )
    estimated_duration_minutes: float = Field(
        ...,
        description="Estimated walking time in minutes (based on 4.5 km/h)"
    )
    vibe_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall route quality score based on requested vibes (0-1)"
    )
    vibe_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Individual vibe scores for transparency"
    )
    transparency_narrative: Optional[str] = Field(
        default=None,
        description="AI-generated explanation of why this route was chosen. "
                    "Uses IBM Granite model to demystify the routing decision."
    )
    algorithm_used: str = Field(
        default="dijkstra",
        description="Routing algorithm used (dijkstra or astar)"
    )
    nodes_explored: int = Field(
        default=0,
        description="Number of graph nodes explored during pathfinding"
    )


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
    """GeoJSON FeatureCollection."""
    type: str = Field(default="FeatureCollection")
    features: list[GeoJSONFeature]


class RouteResponse(BaseModel):
    """
    Successful route response.
    
    Contains GeoJSON that can be directly rendered on a map,
    plus metadata explaining the route characteristics.
    """
    success: bool = Field(default=True)
    geojson: GeoJSONFeatureCollection = Field(
        ...,
        description="GeoJSON FeatureCollection containing the route LineString"
    )
    metadata: RouteMetadata = Field(
        ...,
        description="Route metadata including distance, duration, and vibe scores"
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
                            "coordinates": [
                                [121.0244, 14.5547],
                                [121.0250, 14.5550],
                                [121.0260, 14.5555]
                            ]
                        },
                        "properties": {
                            "stroke": "#22c55e",
                            "stroke-width": 4,
                            "stroke-opacity": 0.8
                        }
                    }]
                },
                "metadata": {
                    "distance_meters": 2450.5,
                    "estimated_duration_minutes": 32.7,
                    "vibe_score": 0.78,
                    "vibe_breakdown": {
                        "greenery": 0.85,
                        "safety_check": 0.72,
                        "walkability": 0.80
                    },
                    "transparency_narrative": "This route was chosen because it passes through Ayala Triangle Gardens, providing excellent greenery coverage. The path uses well-lit residential streets for safety.",
                    "algorithm_used": "astar",
                    "nodes_explored": 342
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response for failed requests."""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Machine-readable error code")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "No walkable path found between the specified points",
                "error_code": "NO_PATH_FOUND",
                "details": {
                    "origin": {"lat": 14.5547, "lon": 121.0244},
                    "destination": {"lat": 14.6000, "lon": 121.1000}
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    graph_loaded: bool = Field(
        default=False,
        description="Whether the OSM graph is loaded and ready"
    )
    cached_regions: list[str] = Field(
        default_factory=list,
        description="List of cached geographic regions"
    )
