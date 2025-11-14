"""
Unit tests for configuration validation and settings.
"""
import os
import tempfile
import pytest
from pathlib import Path
from pydantic import ValidationError

from core.config import Settings, get_settings


@pytest.mark.unit
class TestSettings:
    """Test configuration settings validation."""
    
    def test_default_settings(self):
        """Test default settings creation."""
        settings = Settings()
        
        assert settings.PROJECT_NAME == "RAG Financial AI"
        assert settings.VERSION == "1.0.0"
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is False
        assert settings.SERVER_PORT == 8000
        assert settings.LOG_LEVEL == "INFO"
        assert settings.CHUNK_SIZE == 1000
        assert settings.CHUNK_OVERLAP == 200
        assert settings.MAX_TOKENS == 2048
        assert settings.TEMPERATURE == 0.1
    
    def test_environment_specific_settings(self):
        """Test environment-specific configuration."""
        # Test development environment
        dev_settings = Settings(ENVIRONMENT="development", DEBUG=True)
        assert dev_settings.ENVIRONMENT == "development"
        assert dev_settings.DEBUG is True
        
        # Test production environment
        prod_settings = Settings(
            ENVIRONMENT="production", 
            DEBUG=False,
            SECRET_KEY="production-secret-key-with-32-characters"
        )
        assert prod_settings.ENVIRONMENT == "production"
        assert prod_settings.DEBUG is False
    
    def test_debug_mode_validation(self):
        """Test debug mode validation in production."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(ENVIRONMENT="production", DEBUG=True)
        
        assert "DEBUG mode cannot be enabled in production" in str(exc_info.value)
    
    def test_secret_key_validation(self):
        """Test secret key validation."""
        # Test short secret key
        with pytest.raises(ValidationError) as exc_info:
            Settings(SECRET_KEY="short")
        
        assert "SECRET_KEY must be at least 32 characters long" in str(exc_info.value)
        
        # Test default secret key in production
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="your-secret-key-change-this"
            )
        
        assert "SECRET_KEY must be changed in production" in str(exc_info.value)
    
    def test_port_validation(self):
        """Test server port validation."""
        # Valid ports
        settings = Settings(SERVER_PORT=8080)
        assert settings.SERVER_PORT == 8080
        
        # Invalid ports
        with pytest.raises(ValidationError):
            Settings(SERVER_PORT=0)  # Too low
        
        with pytest.raises(ValidationError):
            Settings(SERVER_PORT=70000)  # Too high
    
    def test_chunk_size_validation(self):
        """Test chunk size and overlap validation."""
        # Valid configuration
        settings = Settings(CHUNK_SIZE=1000, CHUNK_OVERLAP=200)
        assert settings.CHUNK_SIZE == 1000
        assert settings.CHUNK_OVERLAP == 200
        
        # Invalid chunk size (too small)
        with pytest.raises(ValidationError):
            Settings(CHUNK_SIZE=50)
        
        # Invalid chunk size (too large)
        with pytest.raises(ValidationError):
            Settings(CHUNK_SIZE=5000)
        
        # Invalid overlap (larger than chunk size)
        with pytest.raises(ValidationError):
            Settings(CHUNK_SIZE=1000, CHUNK_OVERLAP=1200)
    
    def test_temperature_validation(self):
        """Test model temperature validation."""
        # Valid temperatures
        settings = Settings(TEMPERATURE=0.0)
        assert settings.TEMPERATURE == 0.0
        
        settings = Settings(TEMPERATURE=1.5)
        assert settings.TEMPERATURE == 1.5
        
        # Invalid temperatures
        with pytest.raises(ValidationError):
            Settings(TEMPERATURE=-0.1)  # Too low
        
        with pytest.raises(ValidationError):
            Settings(TEMPERATURE=2.5)  # Too high
    
    def test_max_tokens_validation(self):
        """Test max tokens validation."""
        # Valid token counts
        settings = Settings(MAX_TOKENS=512)
        assert settings.MAX_TOKENS == 512
        
        settings = Settings(MAX_TOKENS=4096)
        assert settings.MAX_TOKENS == 4096
        
        # Invalid token counts
        with pytest.raises(ValidationError):
            Settings(MAX_TOKENS=0)  # Too low
        
        with pytest.raises(ValidationError):
            Settings(MAX_TOKENS=10000)  # Too high
    
    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from string."""
        # Test string parsing
        settings = Settings(ALLOWED_HOSTS="http://localhost:3000,http://localhost:8000,https://example.com")
        
        expected_hosts = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "https://example.com"
        ]
        assert settings.ALLOWED_HOSTS == expected_hosts
        
        # Test list input (should remain unchanged)
        settings = Settings(ALLOWED_HOSTS=["http://localhost:3000", "http://localhost:8080"])
        assert settings.ALLOWED_HOSTS == ["http://localhost:3000", "http://localhost:8080"]
    
    def test_file_types_parsing(self):
        """Test allowed file types parsing."""
        # Test string parsing
        settings = Settings(ALLOWED_FILE_TYPES=".pdf,.docx,.txt,.html")
        expected_types = [".pdf", ".docx", ".txt", ".html"]
        assert settings.ALLOWED_FILE_TYPES == expected_types
        
        # Test list input (should remain unchanged)
        settings = Settings(ALLOWED_FILE_TYPES=[".pdf", ".txt"])
        assert settings.ALLOWED_FILE_TYPES == [".pdf", ".txt"]
    
    def test_directory_validation_and_creation(self):
        """Test directory validation and automatic creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test upload directory creation
            upload_dir = temp_path / "uploads"
            settings = Settings(UPLOAD_DIR=str(upload_dir))
            
            # Directory should be created and path should be absolute
            assert Path(settings.UPLOAD_DIR).exists()
            assert Path(settings.UPLOAD_DIR).is_absolute()
            
            # Test chroma directory creation
            chroma_dir = temp_path / "chroma"
            settings = Settings(CHROMA_PERSIST_DIRECTORY=str(chroma_dir))
            
            assert Path(settings.CHROMA_PERSIST_DIRECTORY).exists()
            assert Path(settings.CHROMA_PERSIST_DIRECTORY).is_absolute()
    
    def test_database_pool_size_validation(self):
        """Test database pool size validation."""
        # Valid pool sizes
        settings = Settings(DATABASE_POOL_SIZE=10)
        assert settings.DATABASE_POOL_SIZE == 10
        
        settings = Settings(DATABASE_POOL_SIZE=50)
        assert settings.DATABASE_POOL_SIZE == 50
        
        # Invalid pool sizes
        with pytest.raises(ValidationError):
            Settings(DATABASE_POOL_SIZE=0)  # Too low
        
        with pytest.raises(ValidationError):
            Settings(DATABASE_POOL_SIZE=150)  # Too high
    
    def test_rate_limiting_settings(self):
        """Test rate limiting configuration."""
        settings = Settings(
            RATE_LIMIT_ENABLED=True,
            RATE_LIMIT_REQUESTS_PER_MINUTE=30
        )
        
        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_REQUESTS_PER_MINUTE == 30
        
        # Test validation
        with pytest.raises(ValidationError):
            Settings(RATE_LIMIT_REQUESTS_PER_MINUTE=0)  # Too low
        
        with pytest.raises(ValidationError):
            Settings(RATE_LIMIT_REQUESTS_PER_MINUTE=2000)  # Too high
    
    def test_timeout_settings(self):
        """Test timeout configuration validation."""
        settings = Settings(
            REQUEST_TIMEOUT=60.0,
            DOCUMENT_PROCESSING_TIMEOUT=300.0
        )
        
        assert settings.REQUEST_TIMEOUT == 60.0
        assert settings.DOCUMENT_PROCESSING_TIMEOUT == 300.0
        
        # Test validation
        with pytest.raises(ValidationError):
            Settings(REQUEST_TIMEOUT=0.5)  # Too low
        
        with pytest.raises(ValidationError):
            Settings(DOCUMENT_PROCESSING_TIMEOUT=2000.0)  # Too high
    
    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            settings = Settings(LOG_LEVEL=level)
            assert settings.LOG_LEVEL == level
        
        # Invalid log level
        with pytest.raises(ValidationError):
            Settings(LOG_LEVEL="INVALID")
    
    def test_vector_db_type_validation(self):
        """Test vector database type validation."""
        # Valid types
        settings = Settings(VECTOR_DB_TYPE="chromadb")
        assert settings.VECTOR_DB_TYPE == "chromadb"
        
        settings = Settings(VECTOR_DB_TYPE="faiss")
        assert settings.VECTOR_DB_TYPE == "faiss"
        
        # Invalid type
        with pytest.raises(ValidationError):
            Settings(VECTOR_DB_TYPE="invalid_db")
    
    def test_feature_flags(self):
        """Test feature flag settings."""
        settings = Settings(
            ENABLE_HEALTH_CHECKS=True,
            ENABLE_METRICS=True,
            ENABLE_TRACING=False,
            ENABLE_CORS=True
        )
        
        assert settings.ENABLE_HEALTH_CHECKS is True
        assert settings.ENABLE_METRICS is True
        assert settings.ENABLE_TRACING is False
        assert settings.ENABLE_CORS is True
    
    def test_optional_external_services(self):
        """Test optional external service configurations."""
        # With external services
        settings = Settings(
            REDIS_URL="redis://localhost:6379",
            SENTRY_DSN="https://example@sentry.io/project"
        )
        
        assert settings.REDIS_URL == "redis://localhost:6379"
        assert settings.SENTRY_DSN == "https://example@sentry.io/project"
        
        # Without external services (should be None)
        settings = Settings()
        assert settings.REDIS_URL is None
        assert settings.SENTRY_DSN is None


@pytest.mark.unit
class TestGetSettings:
    """Test the get_settings function."""
    
    def test_get_settings_function(self):
        """Test get_settings returns valid Settings instance."""
        settings = get_settings()
        
        assert isinstance(settings, Settings)
        assert settings.PROJECT_NAME == "RAG Financial AI"
    
    def test_settings_singleton_behavior(self):
        """Test that settings behave like a singleton."""
        # Note: This is more of a convention test since we're not implementing
        # true singleton behavior, but the global settings instance should be reused
        from core.config import settings as global_settings
        
        assert isinstance(global_settings, Settings)
        assert global_settings.PROJECT_NAME == "RAG Financial AI"


@pytest.mark.unit
class TestEnvironmentVariableOverrides:
    """Test configuration override from environment variables."""
    
    def test_environment_override(self, monkeypatch):
        """Test configuration override from environment variables."""
        # Set environment variables
        monkeypatch.setenv("PROJECT_NAME", "Test Project")
        monkeypatch.setenv("SERVER_PORT", "9000")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        # Create settings (should pick up env vars)
        settings = Settings()
        
        assert settings.PROJECT_NAME == "Test Project"
        assert settings.SERVER_PORT == 9000
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"
    
    def test_case_sensitivity(self, monkeypatch):
        """Test that environment variables are case sensitive."""
        # Set lowercase env var (should not override)
        monkeypatch.setenv("project_name", "lowercase project")
        
        settings = Settings()
        
        # Should still have default value
        assert settings.PROJECT_NAME == "RAG Financial AI"