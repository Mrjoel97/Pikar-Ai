from app.agent import get_revenue_stats, search_business_knowledge, update_initiative_status, create_task
import pytest

def test_get_revenue_stats():
    stats = get_revenue_stats()
    assert isinstance(stats, dict)
    assert "revenue" in stats
    assert isinstance(stats["revenue"], float)

def test_search_business_knowledge_returns_results():
    """Tests that search_business_knowledge returns a dictionary with a 'results' key."""
    result = search_business_knowledge("test query")
    assert isinstance(result, dict)
    assert "results" in result
    assert isinstance(result["results"], list)

def test_update_initiative_status():
    assert isinstance(update_initiative_status("test_id", "in_progress"), dict)

def test_create_task():
    assert isinstance(create_task("test task"), dict)