"""
Request models for the Generative Walking Route Planner API.

These Pydantic models define the schema that watsonx Orchestrate will use
to understand and call our API endpoints.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class RouteMode(str, Enum):
    """Available routing modes."""
    POINT_TO_POINT = "point_to_point"
    CIRCULAR_LOOP = "circular_loop"


class VibeWeights(BaseModel):
    """
    Vibe preferences as normalized floats [0.0 - 1.0].
    
    These weights control the Generative Cost Function:
    Cg = C_base * (1 - Quality_Score)
    
    Higher values = stronger preference for that vibe.
    """
    greenery: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Preference for parks, trees, gardens, and green spaces. "
                    "0.0 = don't care, 1.0 = strongly prefer green routes."
    )
    blue_space: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Preference for water bodies like rivers, lakes, coastline. "
                    "0.0 = don't care, 1.0 = strongly prefer waterfront routes."
    )
    introvert_mode: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Preference for quiet, low-traffic, peaceful areas. "
                    "Avoids busy commercial streets. 0.0 = don't care, 1.0 = maximum quiet."
    )
    extrovert_mode: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Preference for lively, bustling areas with shops, cafes, people. "
                    "0.0 = don't care, 1.0 = maximum liveliness."
    )
    safety_check: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Preference for well-lit streets and safe areas. "
                    "0.0 = don't care, 1.0 = prioritize safety above all."
    )
    walkability: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Preference for pedestrian-friendly paths, sidewalks, footways. "
                    "0.0 = accept any road, 1.0 = strict pedestrian paths only."
    )

    @field_validator('introvert_mode', 'extrovert_mode')
    @classmethod
    def validate_mode_conflict(cls, v, info):
        """Warn if both introvert and extrovert modes are high."""
        # This is just validation; the engine will handle averaging
        return v


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


class NoGoZone(BaseModel):
    """A polygon area to avoid during routing."""
    vertices: list[Coordinate] = Field(
        ...,
        min_length=3,
        description="List of coordinates forming a closed polygon (minimum 3 points)"
    )


class RouteRequest(BaseModel):
    """
    Main request schema for route generation.
    
    This schema is designed to be easily consumed by watsonx Orchestrate
    as a Custom Tool/Skill. The agent will map natural language to these parameters.
    
    Examples of natural language mappings:
    - "nature walk" -> greenery=0.9, blue_space=0.3
    - "safe evening walk" -> safety_check=0.95, walkability=0.8
    - "peaceful stroll" -> introvert_mode=0.8, greenery=0.6
    - "lively city walk" -> extrovert_mode=0.9, walkability=0.7
    """
    mode: RouteMode = Field(
        default=RouteMode.POINT_TO_POINT,
        description="Routing mode: 'point_to_point' for A to B, 'circular_loop' for round trips"
    )
    origin: Coordinate = Field(
        ...,
        description="Starting point coordinates (required)"
    )
    destination: Optional[Coordinate] = Field(
        default=None,
        description="End point coordinates. Required for point_to_point mode, "
                    "ignored for circular_loop mode."
    )
    duration_minutes: int = Field(
        default=30,
        ge=5,
        le=180,
        description="Target walk duration in minutes. Used for circular_loop mode "
                    "to determine loop size. Range: 5-180 minutes."
    )
    vibes: VibeWeights = Field(
        default_factory=VibeWeights,
        description="Vibe preferences controlling route characteristics"
    )
    no_go_zones: list[NoGoZone] = Field(
        default_factory=list,
        description="List of polygon areas to avoid during routing"
    )
    include_narrative: bool = Field(
        default=True,
        description="Whether to generate an AI explanation of the route choice"
    )

    @field_validator('destination')
    @classmethod
    def validate_destination_for_mode(cls, v, info):
        """Destination is required for point_to_point mode."""
        # Note: Full validation happens in the endpoint
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "title": "Nature Loop Walk",
                    "description": "A 45-minute circular walk prioritizing green spaces",
                    "value": {
                        "mode": "circular_loop",
                        "origin": {"lat": 14.5547, "lon": 121.0244},
                        "duration_minutes": 45,
                        "vibes": {
                            "greenery": 0.9,
                            "safety_check": 0.8,
                            "introvert_mode": 0.6,
                            "walkability": 0.8
                        }
                    }
                },
                {
                    "title": "Point to Point Safe Walk",
                    "description": "Safe evening walk from point A to B",
                    "value": {
                        "mode": "point_to_point",
                        "origin": {"lat": 14.5547, "lon": 121.0244},
                        "destination": {"lat": 14.5580, "lon": 121.0280},
                        "vibes": {
                            "safety_check": 0.95,
                            "walkability": 0.9,
                            "greenery": 0.4
                        }
                    }
                },
                {
                    "title": "Lively City Exploration",
                    "description": "Walk through bustling commercial areas",
                    "value": {
                        "mode": "circular_loop",
                        "origin": {"lat": 14.5547, "lon": 121.0244},
                        "duration_minutes": 60,
                        "vibes": {
                            "extrovert_mode": 0.9,
                            "walkability": 0.7,
                            "safety_check": 0.6
                        }
                    }
                }
            ]
        }
