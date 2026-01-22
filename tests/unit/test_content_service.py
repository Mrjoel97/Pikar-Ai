"""Unit tests for ContentService."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.content_service import ContentService


def test_content_service_initialization():
    obj = ContentService()
    assert obj is not None

@patch("app.services.content_service.ingest_document_content")
@pytest.mark.asyncio
async def test_save_content(mock_ingest):
    # Setup
    mock_ingest.return_value = {"success": True, "ids": ["123"]}
    service = ContentService()
    
    # Act
    result = await service.save_content("My Title", "My Content", "agent-1")
    
    # Assert
    assert result["success"] is True
    mock_ingest.assert_called_once()
    # Check args: content, title, document_type, agent_id
    call_args = mock_ingest.call_args[1] # kwargs
    assert call_args["content"] == "My Content"
    assert call_args["title"] == "My Title"
    assert call_args["agent_id"] == "agent-1"
