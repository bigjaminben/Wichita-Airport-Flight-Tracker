"""
Enterprise Configuration Management
Centralized configuration with environment-based settings
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Enterprise application settings with validation"""
    
    # Application Settings
    APP_NAME: str = "Wichita Airport Flight Tracker"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=5001, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    WORKER_CLASS: str = Field(default="sync", env="WORKER_CLASS")
    WORKER_TIMEOUT: int = Field(default=120, env="WORKER_TIMEOUT")
    
    # Security
    SECRET_KEY: str = Field(default="change-this-in-production-use-env-var", env="SECRET_KEY")
    API_KEY_HEADER: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    ALLOWED_API_KEYS: list = Field(default=["enterprise-key-2025"], env="ALLOWED_API_KEYS")
    CORS_ORIGINS: list = Field(default=["*"], env="CORS_ORIGINS")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_DEFAULT: str = Field(default="200 per minute", env="RATE_LIMIT_DEFAULT")
    RATE_LIMIT_STORAGE_URL: str = Field(default="redis://localhost:6379/1", env="RATE_LIMIT_STORAGE_URL")
    
    # Cache Configuration
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    CACHE_TTL: int = Field(default=10, env="CACHE_TTL")
    CACHE_ENABLED: bool = Field(default=True, env="CACHE_ENABLED")
    
    # External API Configuration
    WEATHER_API_KEY: Optional[str] = Field(default=None, env="WEATHER_API_KEY")
    WEATHER_API_URL: str = Field(default="https://api.openweathermap.org/data/2.5", env="WEATHER_API_URL")
    WEATHER_CACHE_TTL: int = Field(default=300, env="WEATHER_CACHE_TTL")
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAIL_MAX: int = Field(default=5, env="CIRCUIT_BREAKER_FAIL_MAX")
    CIRCUIT_BREAKER_TIMEOUT_DURATION: int = Field(default=60, env="CIRCUIT_BREAKER_TIMEOUT_DURATION")
    
    # Retry Configuration
    RETRY_MAX_ATTEMPTS: int = Field(default=3, env="RETRY_MAX_ATTEMPTS")
    RETRY_WAIT_MIN: int = Field(default=1, env="RETRY_WAIT_MIN")
    RETRY_WAIT_MAX: int = Field(default=10, env="RETRY_WAIT_MAX")
    
    # Monitoring & Metrics
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    TRACING_ENABLED: bool = Field(default=True, env="TRACING_ENABLED")
    JAEGER_AGENT_HOST: str = Field(default="localhost", env="JAEGER_AGENT_HOST")
    JAEGER_AGENT_PORT: int = Field(default=6831, env="JAEGER_AGENT_PORT")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json or text
    LOG_FILE: Optional[str] = Field(default="logs/app.log", env="LOG_FILE")
    
    # Database
    HDF5_FILE: str = Field(default="flight_history.h5", env="HDF5_FILE")
    HDF5_COMPRESSION: str = Field(default="gzip", env="HDF5_COMPRESSION")
    
    # Data Refresh
    AUTO_REFRESH_ENABLED: bool = Field(default=True, env="AUTO_REFRESH_ENABLED")
    REFRESH_INTERVAL: int = Field(default=15, env="REFRESH_INTERVAL")
    
    # Performance
    MAX_WORKERS: int = Field(default=10, env="MAX_WORKERS")
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")
    GZIP_COMPRESSION_LEVEL: int = Field(default=6, env="GZIP_COMPRESSION_LEVEL")
    
    @validator('ENVIRONMENT')
    def validate_environment(cls, v):
        allowed = ['development', 'staging', 'production']
        if v not in allowed:
            raise ValueError(f'Environment must be one of {allowed}')
        return v
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'Log level must be one of {allowed}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
