import pytest
from app/services.support_ticket_service import SupportTicketService

def test_support_ticket_service_initialization():
    obj = SupportTicketService()
    assert obj is not None
