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

async def _get_revenue_stats(period: str = "current_month") -> dict:
    """Get revenue statistics for financial analysis from FinancialService.
    
    Args:
        period: Time period for revenue stats (default: current_month).
    
    Returns:
        Dictionary containing revenue amount, currency, period, and status.
    """
    from app.services.financial_service import FinancialService
    
    try:
        service = FinancialService()
        stats = await service.get_revenue_stats(period)
        return stats
    except Exception as e:
        # Fallback to informative error response
        return {
            "revenue": 0.0,
            "currency": "USD",
            "period": period,
            "error": f"Service unavailable: {str(e)}"
        }

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
    """Search business knowledge base for relevant information.
    
    Args:
        query: The search query to find relevant business knowledge.
        
    Returns:
        Dictionary containing search results.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge
        return search_knowledge(query, top_k=3)
    except Exception:
        return {"results": []}


async def _save_content(title: str, content: str) -> dict:
    """Save generated content to the Knowledge Vault via ContentService.
    
    Args:
        title: Title of the content.
        content: The text content to save.
        
    Returns:
        Dictionary confirming save status.
    """
    from app.services.content_service import ContentService
    
    try:
        service = ContentService()
        result = await service.save_content(title, content, agent_id="content-agent")
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_content(content_id: str) -> dict:
    """Retrieve saved content by its ID.
    
    Args:
        content_id: The unique ID of the content.
        
    Returns:
        Dictionary containing the content record.
    """
    from app.services.content_service import ContentService
    
    try:
        service = ContentService()
        result = await service.get_content(content_id)
        return {"success": True, "content": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_content(content_id: str, title: str = None, content: str = None) -> dict:
    """Update existing content.
    
    Args:
        content_id: The unique ID of the content.
        title: New title (optional).
        content: New content text (optional).
        
    Returns:
        Dictionary with updated content.
    """
    from app.services.content_service import ContentService
    
    try:
        service = ContentService()
        result = await service.update_content(content_id, title=title, content=content)
        return {"success": True, "content": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_content(content_type: str = None) -> dict:
    """List saved content items.
    
    Args:
        content_type: Optional filter by type (e.g., 'blog', 'social').
        
    Returns:
        Dictionary with list of content items.
    """
    from app.services.content_service import ContentService
    
    try:
        service = ContentService()
        items = await service.list_content(content_type=content_type)
        return {"success": True, "items": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e), "items": []}


content_agent = Agent(
    name="ContentCreationAgent",
    model=get_model(),
    description="CMO / Creative Director - Creates marketing copy, blog posts, and social media content",
    instruction="""You are the Content Creation Agent. You generate high-quality marketing copy, blog posts, and social media content.

CAPABILITIES:
- Draft content based on brand voice from 'search_knowledge'.
- Save content using 'save_content'.
- Retrieve previously saved content using 'get_content' and 'list_content'.
- Update existing content using 'update_content'.
- Create content calendars and manage drafts.

BEHAVIOR:
- Match the user's brand voice.
- Optimize for engagement and SEO.
- Save and iterate on your best work.
- Keep track of previously created content.""",
    tools=[_search_knowledge, _save_content, _get_content, _update_content, _list_content],
)

def _update_initiative(initiative_id: str, status: str) -> dict:
    """Update initiative status in the system.
    
    Args:
        initiative_id: The unique identifier of the initiative.
        status: The new status (e.g., 'in_progress', 'completed', 'blocked').
        
    Returns:
        Dictionary confirming the status update.
    """
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

async def _create_task(description: str) -> dict:
    """Create a new task in the task management system via TaskService.
    
    Args:
        description: Clear description of what needs to be done.
        
    Returns:
        Dictionary containing task_id, status, and description.
    """
    from app.services.task_service import TaskService
    
    try:
        service = TaskService()
        # agent_id is None for now as we don't have context injection yet
        task = await service.create_task(description, agent_id=None)
        return {
            "task_id": task["id"],
            "status": task["status"],
            "description": description,
            "success": True
        }
    except Exception as e:
        return {
            "error": f"Failed to create task: {str(e)}",
            "description": description,
            "success": False
        }


async def _get_task(task_id: str) -> dict:
    """Retrieve a task by its ID from TaskService.
    
    Args:
        task_id: The unique identifier of the task.
        
    Returns:
        Dictionary containing the task details.
    """
    from app.services.task_service import TaskService
    
    try:
        service = TaskService()
        task = await service.get_task(task_id)
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_task(task_id: str, status: str) -> dict:
    """Update a task's status via TaskService.
    
    Args:
        task_id: The unique identifier of the task.
        status: New status (pending, running, completed, failed).
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.task_service import TaskService
    
    try:
        service = TaskService()
        task = await service.update_task(task_id, status=status)
        return {"success": True, "task": task}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_tasks(status: str = None) -> dict:
    """List tasks, optionally filtered by status.
    
    Args:
        status: Optional status filter (pending, running, completed, failed).
        
    Returns:
        Dictionary containing list of tasks.
    """
    from app.services.task_service import TaskService
    
    try:
        service = TaskService()
        tasks = await service.list_tasks(status=status)
        return {"success": True, "tasks": tasks, "count": len(tasks)}
    except Exception as e:
        return {"success": False, "error": str(e), "tasks": []}


sales_agent = Agent(
    name="SalesIntelligenceAgent",
    model=get_model(),
    description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
    instruction="""You are the Sales Intelligence Agent. You focus on deal scoring, sales enablement, and lead analysis.

CAPABILITIES:
- Score deals and analyze leads.
- Create tasks for follow-ups using 'create_task'.
- View and update task status using 'get_task', 'update_task', 'list_tasks'.
- Draft outreach emails and sales scripts.

BEHAVIOR:
- Be aggressive but empathetic.
- Focus on closing deals and increasing Lifetime Value (LTV).
- Always suggest next steps for each lead.""",
    tools=[_create_task, _get_task, _update_task, _list_tasks],
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
- Create and manage operational tasks using 'create_task', 'get_task', 'update_task', 'list_tasks'.

BEHAVIOR:
- Be systematic and thorough.
- Always look for opportunities to improve efficiency.
- Document processes clearly.""",
    tools=[_create_task, _get_task, _update_task, _list_tasks],
)


# =============================================================================
# HR & Recruitment Agent
# =============================================================================

hr_agent = Agent(
    name="HRRecruitmentAgent",
    model=get_model(),
    description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
    instruction="""You are the HR & Recruitment Agent. You focus on hiring, candidate evaluation, and employee management.

CAPABILITIES:
- Draft job descriptions and interview questions.
- Evaluate candidate profiles and resumes.
- Create onboarding checklists and training plans.
- Provide guidance on HR policies and procedures.

BEHAVIOR:
- Be fair and unbiased in evaluations.
- Focus on culture fit as well as skills.
- Prioritize candidate experience.
- Follow employment law best practices.""",
    tools=[_create_task, _search_knowledge],
)


# =============================================================================
# Compliance & Risk Agent
# =============================================================================

compliance_agent = Agent(
    name="ComplianceRiskAgent",
    model=get_model(),
    description="Legal Counsel - Compliance, risk assessment, and legal guidance",
    instruction="""You are the Compliance & Risk Agent. You focus on legal compliance, risk assessment, and regulatory guidance.

CAPABILITIES:
- Review contracts and legal documents.
- Identify compliance risks and gaps.
- Provide guidance on data privacy (GDPR, CCPA).
- Draft policies and procedures.

BEHAVIOR:
- Be thorough and conservative on risk.
- Always cite relevant regulations when applicable.
- Recommend when to involve external legal counsel.
- Document all risk assessments.""",
    tools=[_search_knowledge],
)


# =============================================================================
# Customer Support Agent
# =============================================================================

customer_support_agent = Agent(
    name="CustomerSupportAgent",
    model=get_model(),
    description="CTO / IT Support - Customer ticket triage, knowledge base, and technical support",
    instruction="""You are the Customer Support Agent. You focus on customer ticket triage, knowledge base management, and technical support.

CAPABILITIES:
- Triage and prioritize support tickets.
- Draft knowledge base articles.
- Create escalation paths for complex issues.
- Generate support metrics and reports.

BEHAVIOR:
- Be empathetic and customer-focused.
- Prioritize resolution time and customer satisfaction.
- Document solutions for future reference.
- Identify patterns in support requests.""",
    tools=[_create_task, _search_knowledge],
)


# =============================================================================
# Data Analysis Agent
# =============================================================================

data_agent = Agent(
    name="DataAnalysisAgent",
    model=get_model(),
    description="Data Analyst - Data validation, anomaly detection, and forecasting",
    instruction="""You are the Data Analysis Agent. You focus on data validation, anomaly detection, and forecasting.

CAPABILITIES:
- Analyze datasets and identify trends.
- Detect anomalies and outliers.
- Create forecasts and predictions.
- Generate data visualizations and reports.

BEHAVIOR:
- Be data-driven and objective.
- Always validate data quality before analysis.
- Present findings clearly with visualizations.
- Quantify uncertainty in predictions.""",
    tools=[_get_revenue_stats, _search_knowledge],
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
    hr_agent,
    compliance_agent,
    customer_support_agent,
    data_agent,
]

__all__ = [
    "financial_agent",
    "content_agent", 
    "strategic_agent",
    "sales_agent",
    "marketing_agent",
    "operations_agent",
    "hr_agent",
    "compliance_agent",
    "customer_support_agent",
    "data_agent",
    "SPECIALIZED_AGENTS",
]
