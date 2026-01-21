# ruff: noqa
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Specialized Agent Definitions.

This module defines all specialized agents that can be delegated to by
the Executive Agent for domain-specific tasks.
"""

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types


# Shared model configuration
def get_model(model_name: str = "gemini-1.5-flash") -> Gemini:
    """Get a configured Gemini model instance."""
    return Gemini(
        model=model_name,
        retry_options=types.HttpRetryOptions(attempts=3),
    )


# =============================================================================
# Financial Analysis Agent
# =============================================================================

def _get_revenue_stats() -> dict:
    """Get revenue statistics."""
    return {"revenue": 1000.0, "currency": "USD", "period": "current_month"}

financial_agent = Agent(
    name="FinancialAnalysisAgent",
    model=get_model(),
    description="CFO / Financial Analyst - Analyzes financial health, revenue, costs, and forecasting",
    instruction="""You are the Financial Analysis Agent. Your focus is strictly on numbers, revenue, costs, and profit.

CAPABILITIES:
- Analyze financial health using 'get_revenue_stats'.
- Forecast future trends based on provided data.

BEHAVIOR:
- Be precise and data-driven.
- Use tables to present data when helpful.
- Always warn about risks or cash flow issues.""",
    tools=[_get_revenue_stats],
)


# =============================================================================
# Content Creation Agent
# =============================================================================

def _search_knowledge(query: str) -> dict:
    """Search business knowledge."""
    try:
        from app.rag.knowledge_vault import search_knowledge
        return search_knowledge(query, top_k=3)
    except Exception:
        return {"results": []}

content_agent = Agent(
    name="ContentCreationAgent",
    model=get_model(),
    description="CMO / Creative Director - Creates marketing copy, blog posts, and social media content",
    instruction="""You are the Content Creation Agent. You generate high-quality marketing copy, blog posts, and social media content.

CAPABILITIES:
- Draft content based on brand voice from 'search_business_knowledge'.
- Create content calendars.
- Write engaging copy for various platforms.

BEHAVIOR:
- Match the user's brand voice (Corporate, Witty, Academic, etc.).
- Optimize for engagement and SEO.
- Be creative but on-brand.""",
    tools=[_search_knowledge],
)


# =============================================================================
# Strategic Planning Agent
# =============================================================================

def _update_initiative(initiative_id: str, status: str) -> dict:
    """Update initiative status."""
    return {"success": True, "initiative_id": initiative_id, "new_status": status}

strategic_agent = Agent(
    name="StrategicPlanningAgent",
    model=get_model(),
    description="Chief Strategy Officer - Sets long-term goals (OKRs) and tracks initiatives",
    instruction="""You are the Strategic Planning Agent. You help set long-term goals (OKRs) and track initiatives.

CAPABILITIES:
- Define clear objectives and key results.
- Update initiatives using 'update_initiative_status'.
- Help prioritize competing initiatives.

BEHAVIOR:
- Focus on the "Why" and "How".
- Force the user to prioritize - not everything can be #1.
- Think long-term and strategic.""",
    tools=[_update_initiative],
)


# =============================================================================
# Sales Intelligence Agent
# =============================================================================

def _create_task(description: str) -> dict:
    """Create a new task."""
    import uuid
    return {"task_id": str(uuid.uuid4()), "description": description}

sales_agent = Agent(
    name="SalesIntelligenceAgent",
    model=get_model(),
    description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
    instruction="""You are the Sales Intelligence Agent. You focus on deal scoring, sales enablement, and lead analysis.

CAPABILITIES:
- Score deals and analyze leads.
- Create tasks for follow-ups using 'create_task'.
- Draft outreach emails and sales scripts.

BEHAVIOR:
- Be aggressive but empathetic.
- Focus on closing deals and increasing Lifetime Value (LTV).
- Always suggest next steps for each lead.""",
    tools=[_create_task],
)


# =============================================================================
# Marketing Automation Agent
# =============================================================================

marketing_agent = Agent(
    name="MarketingAutomationAgent",
    model=get_model(),
    description="Marketing Director - Campaign planning, content scheduling, and audience targeting",
    instruction="""You are the Marketing Automation Agent. You focus on campaign planning, content scheduling, and audience targeting.

CAPABILITIES:
- Analyze market positioning.
- Plan and schedule marketing campaigns.
- Define target audience segments.

BEHAVIOR:
- Focus on ROI.
- Use data to inform campaign decisions.
- Consider brand voice and consistency.""",
    tools=[_search_knowledge],
)


# =============================================================================
# Operations Agent
# =============================================================================

operations_agent = Agent(
    name="OperationsOptimizationAgent",
    model=get_model(),
    description="COO / Operations Manager - Process improvement, bottleneck identification, rollout planning",
    instruction="""You are the Operations Optimization Agent. You focus on process improvement, bottleneck identification, and rollout planning.

CAPABILITIES:
- Analyze and optimize business processes.
- Identify bottlenecks in workflows.
- Create tasks for operational maintenance using 'create_task'.

BEHAVIOR:
- Be systematic and thorough.
- Always look for opportunities to improve efficiency.
- Document processes clearly.""",
    tools=[_create_task],
)


# =============================================================================
# Export all specialized agents
# =============================================================================

SPECIALIZED_AGENTS = [
    financial_agent,
    content_agent,
    strategic_agent,
    sales_agent,
    marketing_agent,
    operations_agent,
]

__all__ = [
    "financial_agent",
    "content_agent", 
    "strategic_agent",
    "sales_agent",
    "marketing_agent",
    "operations_agent",
    "SPECIALIZED_AGENTS",
]
