"""
Configuration settings for the application with comprehensive validation.
"""
from pydantic import validator, Field, AnyHttpUrl
from pydantic_settings import BaseSettings
from typing import List, Optional, Literal
import os
import secrets
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with comprehensive validation."""
    
    # Environment
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    
    # Application
    PROJECT_NAME: str = Field(default="RAG Financial AI", description="Project name")
    VERSION: str = Field(default="1.0.0", description="Application version")
    API_V1_STR: str = Field(default="/api/v1", description="API version prefix")
    DESCRIPTION: str = Field(
        default="A production-ready RAG system for financial document analysis using GPT-OSS:20B",
        description="Application description"
    )
    
    # Server
    SERVER_HOST: str = Field(default="0.0.0.0", description="Server host")
    SERVER_PORT: int = Field(default=8000, ge=1, le=65535, description="Server port")
    
    # CORS
    ALLOWED_HOSTS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Ollama/GPT-OSS Settings
    OLLAMA_BASE_URL: AnyHttpUrl = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    GPT_OSS_MODEL: str = Field(
        default="llama3:latest",
        description="GPT-OSS model name"
    )
    MAX_TOKENS: int = Field(
        default=2048,
        ge=1,
        le=8192,
        description="Maximum tokens per response"
    )
    TEMPERATURE: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Model temperature"
    )
    REQUEST_TIMEOUT: float = Field(
        default=120.0,
        ge=1.0,
        le=600.0,
        description="Request timeout in seconds"
    )
    
    # Vector Database
    VECTOR_DB_TYPE: Literal["chromadb", "faiss"] = Field(
        default="chromadb",
        description="Vector database type"
    )
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="../vector-store/chroma_db",
        description="ChromaDB persistence directory"
    )
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace embedding model name"
    )
    
    @validator("CHROMA_PERSIST_DIRECTORY")
    def validate_chroma_directory(cls, v):
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())
    
    # Document Processing
    CHUNK_SIZE: int = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Text chunk size for processing"
    )
    CHUNK_OVERLAP: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Overlap between chunks"
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum upload file size in MB"
    )
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=[".pdf", ".docx", ".txt", ".html", ".md"],
        description="Allowed file types for upload"
    )
    
    @validator("CHUNK_OVERLAP")
    def validate_chunk_overlap(cls, v, values):
        if "CHUNK_SIZE" in values and v >= values["CHUNK_SIZE"]:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    # Storage
    UPLOAD_DIR: str = Field(default="uploads", description="Upload directory")
    
    @validator("UPLOAD_DIR")
    def validate_upload_directory(cls, v):
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())
    
    # Redis Cache
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    CACHE_TTL: int = Field(
        default=300,
        ge=0,
        le=3600,
        description="Default cache TTL in seconds"
    )
    
    # Database (for metadata storage)
    DATABASE_URL: str = Field(
        default="sqlite:///./financial_ai.db",
        description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Database connection pool size"
    )
    
    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    ENABLE_JSON_LOGGING: bool = Field(
        default=True,
        description="Enable structured JSON logging"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for encryption"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Access token expiration in minutes"
    )
    ENABLE_CORS: bool = Field(default=True, description="Enable CORS middleware")
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Rate limit requests per minute"
    )
    
    # Performance
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum concurrent requests"
    )
    DOCUMENT_PROCESSING_TIMEOUT: float = Field(
        default=300.0,
        ge=10.0,
        le=1800.0,
        description="Document processing timeout in seconds"
    )
    
    # Feature Flags
    ENABLE_HEALTH_CHECKS: bool = Field(default=True, description="Enable health check endpoints")
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    ENABLE_TRACING: bool = Field(default=False, description="Enable distributed tracing")
    
    # External Services
    REDIS_URL: Optional[str] = Field(default=None, description="Redis connection URL for caching")
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        if v == "your-secret-key-change-this":
            env = values.get("ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
            if env == "production":
                raise ValueError("SECRET_KEY must be changed in production")
        if len(v) < 32 and v != "your-secret-key-change-this":
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("DEBUG")
    def validate_debug_mode(cls, v, values):
        if "ENVIRONMENT" in values:
            if values["ENVIRONMENT"] == "production" and v:
                raise ValueError("DEBUG mode cannot be enabled in production")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        use_enum_values = True
        validate_assignment = True
        
        @classmethod
        def schema_extra(cls, schema, model_type):
            """Add schema extra information."""
            schema["title"] = "RAG Financial AI Configuration"
            schema["description"] = "Configuration settings for RAG Financial AI application"


def get_settings() -> Settings:
    """Get validated settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
