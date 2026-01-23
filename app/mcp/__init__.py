"""MCP Connector Module for Pikar AI.

This module provides a built-in MCP (Model Context Protocol) connector that enables
agents to access external services securely. The MCP connector is a system-managed
component - users cannot configure their own MCP servers.

Features:
- Privacy-safe web search (Tavily) with PII filtering
- Web scraping (Firecrawl) for research and content extraction
- Landing page generation with HTML/React components
- Form submission handling with Supabase storage
- Email notifications for form submissions
- CRM integration (HubSpot) for lead management
- Audit logging for all external service calls

Usage:
    from app.mcp import get_mcp_tools, MCPConnector

    # Get MCP tools for an agent
    tools = get_mcp_tools(["web_search", "web_scrape", "landing_page"])

    # Or use the connector directly
    connector = MCPConnector()
    results = await connector.web_search("market research AI trends")

    # For ADK Agent integration, use get_mcp_agent_tools
    from app.mcp import get_mcp_agent_tools

    agent = Agent(
        name="MyAgent",
        tools=[*existing_tools, *get_mcp_agent_tools()],
    )
"""

from app.mcp.connector import MCPConnector, get_mcp_tools
from app.mcp.agent_tools import (
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
    get_mcp_agent_tools,
    MCP_TOOLS,
)

__all__ = [
    # Connector
    "MCPConnector",
    "get_mcp_tools",
    # ADK Agent Tools
    "mcp_web_search",
    "mcp_web_scrape",
    "mcp_generate_landing_page",
    "get_mcp_agent_tools",
    "MCP_TOOLS",
]

