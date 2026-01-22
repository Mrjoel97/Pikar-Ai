"""Unit tests for SupportTicketService.

Tests CRUD operations for tickets used by CustomerSupportAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestSupportTicketService:
    """Test suite for SupportTicketService."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create SupportTicketService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
        }):
            with patch('app.services.support_ticket_service.create_client') as mock_create:
                mock_create.return_value = mock_supabase_client
                from app.services.support_ticket_service import SupportTicketService
                return SupportTicketService()

    def test_initialization_success(self, service):
        """Test that service initializes correctly."""
        assert service is not None
        assert service._table_name == "support_tickets"

    @pytest.mark.asyncio
    async def test_create_ticket(self, service, mock_supabase_client):
        """Test creating a ticket."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "tkt-1",
            "subject": "Login Issue",
            "status": "new"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.create_ticket(
            subject="Login Issue",
            description="Can't login",
            customer_email="user@example.com"
        )
        assert result["id"] == "tkt-1"
        assert result["status"] == "new"

    @pytest.mark.asyncio
    async def test_get_ticket(self, service, mock_supabase_client):
        """Test retrieving a ticket."""
        mock_response = MagicMock()
        mock_response.data = {"id": "tkt-1", "subject": "Issue"}
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        result = await service.get_ticket("tkt-1")
        assert result["id"] == "tkt-1"

    @pytest.mark.asyncio
    async def test_update_ticket(self, service, mock_supabase_client):
        """Test updating a ticket."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "tkt-1", "status": "resolved"}]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.update_ticket("tkt-1", status="resolved")
        assert result["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_list_tickets(self, service, mock_supabase_client):
        """Test listing tickets."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "tkt-1"}, {"id": "tkt-2"}]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        result = await service.list_tickets(status="new")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_delete_ticket(self, service, mock_supabase_client):
        """Test deleting a ticket."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "tkt-1"}]
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.delete_ticket("tkt-1")
        assert result is True
