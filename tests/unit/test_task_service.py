
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

import pytest
from app.services.task_service import TaskService


@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
def test_task_service_initialization(mock_create_client):
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    service = TaskService()
    assert service is not None
    assert service.client == mock_client

@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_create_task(mock_create_client):
    # Setup
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    # Mock the chain: table('ai_jobs').insert().execute()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()
    
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute
    
    # Mock response
    mock_execute.data = [{"id": "123", "status": "pending"}]
    
    service = TaskService()
    
    # Act
    result = await service.create_task("Test Task", "123", "abc")
    
    # Assert
    mock_client.table.assert_called_with("ai_jobs")
    mock_table.insert.assert_called()
    assert result["id"] == "123"
    assert result["status"] == "pending"
