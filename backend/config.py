"""
Configuration management for the routing backend.
Loads environment variables and provides typed settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server config
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # IBM watsonx credentials (for optional narrative generation)
    watsonx_api_key: str = Field(default="", description="IBM watsonx API key")
    watsonx_project_id: str = Field(default="", description="IBM watsonx project ID")
    watsonx_url: str = Field(
        default="https://us-south.ml.cloud.ibm.com",
        description="IBM watsonx API URL"
    )
    
    # Allowed models per hackathon rules (NO llama-3-405b-instruct or mistral-medium)
    watsonx_model_id: str = Field(
        default="ibm/granite-13b-chat-v2",
        description="Model ID for narrative generation"
    )
    
    # Graph caching
    cache_dir: Path = Field(
        default=Path(__file__).parent / "data" / "cache",
        description="Directory for cached OSM graphs"
    )
    
    # Default location: Metro Manila (Makati/BGC - best OSM coverage in Philippines)
    default_lat: float = Field(default=14.5547, description="Default latitude")
    default_lon: float = Field(default=121.0244, description="Default longitude")
    default_place: str = Field(default="Makati, Metro Manila, Philippines")
    
    # Walking speed assumptions
    walking_speed_kmh: float = Field(default=4.5, description="Average walking speed km/h")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
