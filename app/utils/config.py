"""Configuration and utilities"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Temporal configuration
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    
    # Database configuration
    database_url: str = "postgresql://app_user:app_password@localhost:5433/orders"
    
    # Task queues
    order_task_queue: str = "order-processing"
    shipping_task_queue: str = "shipping-processing"
    
    # Timeouts (in seconds)
    workflow_timeout: int = 15
    manual_review_timeout: int = 10
    activity_timeout: int = 5
    
    # Retry configuration
    max_retry_attempts: int = 3
    initial_retry_interval: int = 1
    max_retry_interval: int = 10
    backoff_coefficient: float = 2.0
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
