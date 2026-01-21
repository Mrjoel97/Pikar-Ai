
import sys
from unittest.mock import MagicMock, patch

# Mock google.adk components
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = MagicMock()
sys.modules["google.genai.types"] = MagicMock()
sys.modules["google.adk"] = MagicMock()
sys.modules["google.adk.agents"] = MagicMock()
sys.modules["google.adk.apps"] = MagicMock()
sys.modules["google.adk.models"] = MagicMock()
sys.modules["google.adk.agents.context_cache_config"] = MagicMock()
sys.modules["google.adk.apps.events_compaction_config"] = MagicMock()
# Mock opentelemetry to avoid version issues
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.instrumentation"] = MagicMock()
sys.modules["opentelemetry.instrumentation.google_genai"] = MagicMock()

# Mock internal dependencies that trigger import errors
sys.modules["app.rag.embedding_service"] = MagicMock()

import pytest
from app.services.content_service import ContentService

def test_content_service_initialization():
    obj = ContentService()
    assert obj is not None

@patch("app.rag.knowledge_vault.ingest_document_content")
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
