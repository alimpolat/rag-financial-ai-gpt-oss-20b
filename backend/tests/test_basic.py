"""Basic tests to verify test infrastructure."""
import pytest


def test_basic_assertion():
    """Test that basic assertions work."""
    assert 2 + 2 == 4


def test_import_core_modules():
    """Test that core modules can be imported."""
    from core.config import settings
    from core.exceptions import BaseRAGException
    from core.logging import get_logger
    
    assert settings is not None
    assert BaseRAGException is not None
    assert get_logger is not None


@pytest.mark.asyncio
async def test_async_function():
    """Test that async tests work."""
    import asyncio
    
    async def sample_async():
        await asyncio.sleep(0.01)
        return "success"
    
    result = await sample_async()
    assert result == "success"


def test_exception_handling():
    """Test exception handling works."""
    from core.exceptions import ValidationError
    
    with pytest.raises(ValidationError):
        raise ValidationError("Test error")