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

# Import enhanced skill-based tools
from app.agents.enhanced_tools import (
    # Core tools
    use_skill,
    list_available_skills,
    # Domain-specific tools
    analyze_financial_health,
    get_revenue_forecast_guidance,
    calculate_burn_rate_guidance,
    analyze_process_bottlenecks,
    get_sop_template,
    get_anomaly_detection_guidance,
    get_trend_analysis_framework,
    analyze_ticket_sentiment,
    assess_churn_risk,
    get_lead_qualification_framework,
    get_objection_handling_scripts,
    get_competitive_analysis_framework,
    generate_campaign_ideas,
    get_seo_checklist,
    get_social_media_guide,
    get_resume_screening_framework,
    generate_interview_questions,
    get_turnover_analysis_framework,
    get_gdpr_audit_checklist,
    get_risk_assessment_matrix,
    get_blog_writing_framework,
    get_social_content_templates,
    generate_image,
    generate_short_video,
)

# Import MCP tools for web search, scraping, and landing page generation
from app.mcp.agent_tools import (
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
)


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
- Get revenue statistics using 'get_revenue_stats'.
- Analyze financial health using 'analyze_financial_health' for comprehensive frameworks.
- Get forecasting methodologies using 'get_revenue_forecast_guidance'.
- Calculate burn rate and runway using 'calculate_burn_rate_guidance'.
- Search for market data and financial news using 'mcp_web_search' (privacy-safe).
- Access any skill using 'use_skill' with the skill name.

BEHAVIOR:
- Be precise and data-driven.
- Use tables to present data when helpful.
- Always warn about risks or cash flow issues.
- Leverage skills for professional analysis frameworks.
- Use web search for up-to-date market data and financial trends.""",
    tools=[_get_revenue_stats, analyze_financial_health, get_revenue_forecast_guidance, calculate_burn_rate_guidance, mcp_web_search, use_skill],
)


def create_financial_agent(name_suffix: str = "") -> Agent:
    """Create a fresh FinancialAnalysisAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"FinancialAnalysisAgent{name_suffix}" if name_suffix else "FinancialAnalysisAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CFO / Financial Analyst - Analyzes financial health, revenue, costs, and forecasting",
        instruction="""You are the Financial Analysis Agent. Your focus is strictly on numbers, revenue, costs, and profit.

CAPABILITIES:
- Get revenue statistics using 'get_revenue_stats'.
- Analyze financial health using 'analyze_financial_health' for comprehensive frameworks.
- Get forecasting methodologies using 'get_revenue_forecast_guidance'.
- Calculate burn rate and runway using 'calculate_burn_rate_guidance'.
- Search for market data and financial news using 'mcp_web_search' (privacy-safe).
- Access any skill using 'use_skill' with the skill name.

BEHAVIOR:
- Be precise and data-driven.
- Use tables to present data when helpful.
- Always warn about risks or cash flow issues.
- Leverage skills for professional analysis frameworks.
- Use web search for up-to-date market data and financial trends.""",
        tools=[_get_revenue_stats, analyze_financial_health, get_revenue_forecast_guidance, calculate_burn_rate_guidance, mcp_web_search, use_skill],
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
    description="CMO / Creative Director - Creates marketing copy, blog posts, social media content, images, and videos",
    instruction="""You are the Content Creation Agent. You generate high-quality marketing content including text, images, and videos.

CAPABILITIES:
- Draft content based on brand voice from 'search_knowledge'.
- Get blog writing frameworks using 'get_blog_writing_framework'.
- Get social content templates using 'get_social_content_templates'.
- Generate images using 'generate_image' with text prompts.
- Generate short videos using 'generate_short_video' with text prompts.
- Save content using 'save_content'.
- Retrieve saved content using 'get_content' and 'list_content'.
- Update existing content using 'update_content'.
- Research topics using 'mcp_web_search' for up-to-date information.
- Extract content from web pages using 'mcp_web_scrape'.
- Generate landing pages using 'mcp_generate_landing_page'.

BEHAVIOR:
- Match the user's brand voice.
- Optimize for engagement and SEO.
- Use skills for professional content frameworks.
- Always offer to generate supporting images/videos.
- Save and iterate on your best work.
- Use web search for trending topics and research.""",
    tools=[_search_knowledge, _save_content, _get_content, _update_content, _list_content, get_blog_writing_framework, get_social_content_templates, generate_image, generate_short_video, mcp_web_search, mcp_web_scrape, mcp_generate_landing_page, use_skill],
)


def create_content_agent(name_suffix: str = "") -> Agent:
    """Create a fresh ContentCreationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"ContentCreationAgent{name_suffix}" if name_suffix else "ContentCreationAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CMO / Creative Director - Creates marketing copy, blog posts, social media content, images, and videos",
        instruction="""You are the Content Creation Agent. You generate high-quality marketing content including text, images, and videos.

CAPABILITIES:
- Draft content based on brand voice from 'search_knowledge'.
- Get blog writing frameworks using 'get_blog_writing_framework'.
- Get social content templates using 'get_social_content_templates'.
- Generate images using 'generate_image' with text prompts.
- Generate short videos using 'generate_short_video' with text prompts.
- Save content using 'save_content'.
- Retrieve saved content using 'get_content' and 'list_content'.
- Update existing content using 'update_content'.
- Research topics using 'mcp_web_search' for up-to-date information.
- Extract content from web pages using 'mcp_web_scrape'.
- Generate landing pages using 'mcp_generate_landing_page'.

BEHAVIOR:
- Match the user's brand voice.
- Optimize for engagement and SEO.
- Use skills for professional content frameworks.
- Always offer to generate supporting images/videos.
- Save and iterate on your best work.
- Use web search for trending topics and research.""",
        tools=[_search_knowledge, _save_content, _get_content, _update_content, _list_content, get_blog_writing_framework, get_social_content_templates, generate_image, generate_short_video, mcp_web_search, mcp_web_scrape, mcp_generate_landing_page, use_skill],
    )


# =============================================================================
# Strategic Planning Agent
# =============================================================================

async def _create_initiative(title: str, description: str, priority: str = "medium") -> dict:
    """Create a new strategic initiative.
    
    Args:
        title: Title of the initiative.
        description: Description of the initiative goals.
        priority: Priority level (low, medium, high, critical).
        
    Returns:
        Dictionary containing the created initiative.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiative = await service.create_initiative(title, description, priority)
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_initiative(initiative_id: str) -> dict:
    """Retrieve an initiative by ID.
    
    Args:
        initiative_id: The unique identifier of the initiative.
        
    Returns:
        Dictionary containing the initiative details.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiative = await service.get_initiative(initiative_id)
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_initiative(initiative_id: str, status: str, progress: int = None) -> dict:
    """Update initiative status and progress.
    
    Args:
        initiative_id: The unique identifier of the initiative.
        status: The new status (draft, active, completed, on_hold).
        progress: Optional progress percentage (0-100).
        
    Returns:
        Dictionary confirming the status update.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiative = await service.update_initiative(initiative_id, status=status, progress=progress)
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_initiatives(status: str = None) -> dict:
    """List all initiatives, optionally filtered by status.
    
    Args:
        status: Optional status filter (draft, active, completed, on_hold).
        
    Returns:
        Dictionary containing list of initiatives.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiatives = await service.list_initiatives(status=status)
        return {"success": True, "initiatives": initiatives, "count": len(initiatives)}
    except Exception as e:
        return {"success": False, "error": str(e), "initiatives": []}


strategic_agent = Agent(
    name="StrategicPlanningAgent",
    model=get_model(),
    description="Chief Strategy Officer - Sets long-term goals (OKRs) and tracks initiatives",
    instruction="""You are the Strategic Planning Agent. You help set long-term goals (OKRs) and track initiatives.

CAPABILITIES:
- Create initiatives using 'create_initiative'.
- View initiative details using 'get_initiative'.
- Update initiative status and progress using 'update_initiative'.
- List all initiatives using 'list_initiatives'.
- Help prioritize competing initiatives.
- Research market trends using 'mcp_web_search' (privacy-safe).
- Extract competitor information using 'mcp_web_scrape'.

BEHAVIOR:
- Focus on the "Why" and "How".
- Force the user to prioritize - not everything can be #1.
- Think long-term and strategic.
- Track progress on all active initiatives.
- Use web search for market intelligence and competitive analysis.""",
    tools=[_create_initiative, _get_initiative, _update_initiative, _list_initiatives, mcp_web_search, mcp_web_scrape],
)


def create_strategic_agent(name_suffix: str = "") -> Agent:
    """Create a fresh StrategicPlanningAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"StrategicPlanningAgent{name_suffix}" if name_suffix else "StrategicPlanningAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Chief Strategy Officer - Sets long-term goals (OKRs) and tracks initiatives",
        instruction="""You are the Strategic Planning Agent. You help set long-term goals (OKRs) and track initiatives.

CAPABILITIES:
- Create initiatives using 'create_initiative'.
- View initiative details using 'get_initiative'.
- Update initiative status and progress using 'update_initiative'.
- List all initiatives using 'list_initiatives'.
- Help prioritize competing initiatives.
- Research market trends using 'mcp_web_search' (privacy-safe).
- Extract competitor information using 'mcp_web_scrape'.

BEHAVIOR:
- Focus on the "Why" and "How".
- Force the user to prioritize - not everything can be #1.
- Think long-term and strategic.
- Track progress on all active initiatives.
- Use web search for market intelligence and competitive analysis.""",
        tools=[_create_initiative, _get_initiative, _update_initiative, _list_initiatives, mcp_web_search, mcp_web_scrape],
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
- Score leads using 'get_lead_qualification_framework' for BANT/MEDDIC/CHAMP frameworks.
- Handle objections using 'get_objection_handling_scripts' for proven techniques.
- Analyze competitors using 'get_competitive_analysis_framework'.
- Create tasks for follow-ups using 'create_task'.
- View and update task status using 'get_task', 'update_task', 'list_tasks'.
- Draft outreach emails and sales scripts.
- Research leads and companies using 'mcp_web_search' (privacy-safe).
- Extract prospect information using 'mcp_web_scrape'.

BEHAVIOR:
- Be aggressive but empathetic.
- Focus on closing deals and increasing Lifetime Value (LTV).
- Always qualify leads before extensive engagement.
- Use competitive intelligence to position against rivals.
- Research prospects and their companies before outreach.""",
    tools=[_create_task, _get_task, _update_task, _list_tasks, get_lead_qualification_framework, get_objection_handling_scripts, get_competitive_analysis_framework, mcp_web_search, mcp_web_scrape, use_skill],
)


def create_sales_agent(name_suffix: str = "") -> Agent:
    """Create a fresh SalesIntelligenceAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"SalesIntelligenceAgent{name_suffix}" if name_suffix else "SalesIntelligenceAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
        instruction="""You are the Sales Intelligence Agent. You focus on deal scoring, sales enablement, and lead analysis.

CAPABILITIES:
- Score leads using 'get_lead_qualification_framework' for BANT/MEDDIC/CHAMP frameworks.
- Handle objections using 'get_objection_handling_scripts' for proven techniques.
- Analyze competitors using 'get_competitive_analysis_framework'.
- Create tasks for follow-ups using 'create_task'.
- View and update task status using 'get_task', 'update_task', 'list_tasks'.
- Draft outreach emails and sales scripts.
- Research leads and companies using 'mcp_web_search' (privacy-safe).
- Extract prospect information using 'mcp_web_scrape'.

BEHAVIOR:
- Be aggressive but empathetic.
- Focus on closing deals and increasing Lifetime Value (LTV).
- Always qualify leads before extensive engagement.
- Use competitive intelligence to position against rivals.
- Research prospects and their companies before outreach.""",
        tools=[_create_task, _get_task, _update_task, _list_tasks, get_lead_qualification_framework, get_objection_handling_scripts, get_competitive_analysis_framework, mcp_web_search, mcp_web_scrape, use_skill],
    )


# =============================================================================
# Marketing Automation Agent
# =============================================================================

async def _create_campaign(name: str, campaign_type: str, target_audience: str) -> dict:
    """Create a new marketing campaign.
    
    Args:
        name: Campaign name.
        campaign_type: Type (email, social, content, paid_ads).
        target_audience: Target audience description.
        
    Returns:
        Dictionary containing the created campaign.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        service = CampaignService()
        campaign = await service.create_campaign(name, campaign_type, target_audience)
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_campaign(campaign_id: str) -> dict:
    """Retrieve a campaign by ID.
    
    Args:
        campaign_id: The unique campaign ID.
        
    Returns:
        Dictionary containing the campaign details.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        service = CampaignService()
        campaign = await service.get_campaign(campaign_id)
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_campaign(campaign_id: str, status: str = None, name: str = None) -> dict:
    """Update a campaign's status or name.
    
    Args:
        campaign_id: The unique campaign ID.
        status: New status (draft, active, paused, completed).
        name: New campaign name.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        service = CampaignService()
        campaign = await service.update_campaign(campaign_id, status=status, name=name)
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_campaigns(status: str = None, campaign_type: str = None) -> dict:
    """List campaigns with optional filters.
    
    Args:
        status: Filter by campaign status.
        campaign_type: Filter by campaign type.
        
    Returns:
        Dictionary containing list of campaigns.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        service = CampaignService()
        campaigns = await service.list_campaigns(status=status, campaign_type=campaign_type)
        return {"success": True, "campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        return {"success": False, "error": str(e), "campaigns": []}


async def _record_campaign_metrics(campaign_id: str, impressions: int = 0, clicks: int = 0, conversions: int = 0) -> dict:
    """Record performance metrics for a campaign.
    
    Args:
        campaign_id: The unique campaign ID.
        impressions: Number of impressions.
        clicks: Number of clicks.
        conversions: Number of conversions.
        
    Returns:
        Dictionary with updated campaign metrics.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        service = CampaignService()
        result = await service.record_metrics(campaign_id, impressions, clicks, conversions)
        return {"success": True, "campaign": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


marketing_agent = Agent(
    name="MarketingAutomationAgent",
    model=get_model(),
    description="Marketing Director - Campaign planning, content scheduling, and audience targeting",
    instruction="""You are the Marketing Automation Agent. You focus on campaign planning, content scheduling, and audience targeting.

CAPABILITIES:
- Generate campaign ideas using 'generate_campaign_ideas' for creative frameworks.
- Plan and schedule marketing campaigns using 'create_campaign'.
- Manage campaigns using 'get_campaign', 'update_campaign', 'list_campaigns'.
- Track campaign performance using 'record_campaign_metrics'.
- Optimize SEO using 'get_seo_checklist' for comprehensive audits.
- Master social media using 'get_social_media_guide' for platform best practices.
- Search knowledge base for brand voice and context.
- Research trends and competitors using 'mcp_web_search' (privacy-safe).
- Extract competitor content using 'mcp_web_scrape'.
- Generate landing pages using 'mcp_generate_landing_page'.

BEHAVIOR:
- Focus on ROI.
- Use data to inform campaign decisions.
- Consider brand voice and consistency.
- Leverage skills for professional marketing frameworks.
- Research market trends and competitor campaigns.""",
    tools=[_search_knowledge, _create_campaign, _get_campaign, _update_campaign, _list_campaigns, _record_campaign_metrics, generate_campaign_ideas, get_seo_checklist, get_social_media_guide, mcp_web_search, mcp_web_scrape, mcp_generate_landing_page, use_skill],
)


def create_marketing_agent(name_suffix: str = "") -> Agent:
    """Create a fresh MarketingAutomationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"MarketingAutomationAgent{name_suffix}" if name_suffix else "MarketingAutomationAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Marketing Director - Campaign planning, content scheduling, and audience targeting",
        instruction="""You are the Marketing Automation Agent. You focus on campaign planning, content scheduling, and audience targeting.

CAPABILITIES:
- Generate campaign ideas using 'generate_campaign_ideas' for creative frameworks.
- Plan and schedule marketing campaigns using 'create_campaign'.
- Manage campaigns using 'get_campaign', 'update_campaign', 'list_campaigns'.
- Track campaign performance using 'record_campaign_metrics'.
- Optimize SEO using 'get_seo_checklist' for comprehensive audits.
- Master social media using 'get_social_media_guide' for platform best practices.
- Search knowledge base for brand voice and context.
- Research trends and competitors using 'mcp_web_search' (privacy-safe).
- Extract competitor content using 'mcp_web_scrape'.
- Generate landing pages using 'mcp_generate_landing_page'.

BEHAVIOR:
- Focus on ROI.
- Use data to inform campaign decisions.
- Consider brand voice and consistency.
- Leverage skills for professional marketing frameworks.
- Research market trends and competitor campaigns.""",
        tools=[_search_knowledge, _create_campaign, _get_campaign, _update_campaign, _list_campaigns, _record_campaign_metrics, generate_campaign_ideas, get_seo_checklist, get_social_media_guide, mcp_web_search, mcp_web_scrape, mcp_generate_landing_page, use_skill],
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
- Analyze bottlenecks using 'analyze_process_bottlenecks' for Theory of Constraints methodology.
- Create SOPs using 'get_sop_template' for standardized documentation.
- Analyze and optimize business processes.
- Create and manage operational tasks using 'create_task', 'get_task', 'update_task', 'list_tasks'.
- Research industry best practices using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be systematic and thorough.
- Always look for opportunities to improve efficiency.
- Document processes clearly using SOP frameworks.
- Use proven methodologies for bottleneck resolution.
- Research industry benchmarks and operational best practices.""",
    tools=[_create_task, _get_task, _update_task, _list_tasks, analyze_process_bottlenecks, get_sop_template, mcp_web_search, use_skill],
)


def create_operations_agent(name_suffix: str = "") -> Agent:
    """Create a fresh OperationsOptimizationAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"OperationsOptimizationAgent{name_suffix}" if name_suffix else "OperationsOptimizationAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="COO / Operations Manager - Process improvement, bottleneck identification, rollout planning",
        instruction="""You are the Operations Optimization Agent. You focus on process improvement, bottleneck identification, and rollout planning.

CAPABILITIES:
- Analyze bottlenecks using 'analyze_process_bottlenecks' for Theory of Constraints methodology.
- Create SOPs using 'get_sop_template' for standardized documentation.
- Analyze and optimize business processes.
- Create and manage operational tasks using 'create_task', 'get_task', 'update_task', 'list_tasks'.
- Research industry best practices using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be systematic and thorough.
- Always look for opportunities to improve efficiency.
- Document processes clearly using SOP frameworks.
- Use proven methodologies for bottleneck resolution.
- Research industry benchmarks and operational best practices.""",
        tools=[_create_task, _get_task, _update_task, _list_tasks, analyze_process_bottlenecks, get_sop_template, mcp_web_search, use_skill],
    )


# =============================================================================
# =============================================================================
# HR & Recruitment Agent
# =============================================================================

async def _create_job(title: str, department: str, description: str, requirements: str) -> dict:
    """Create a new job posting.
    
    Args:
        title: Job title.
        department: Department name.
        description: Job description.
        requirements: Job requirements.
        
    Returns:
        Dictionary containing the created job.
    """
    from app.services.recruitment_service import RecruitmentService
    
    try:
        service = RecruitmentService()
        job = await service.create_job(title, department, description, requirements)
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_job(job_id: str) -> dict:
    """Retrieve a job by ID.
    
    Args:
        job_id: The unique job ID.
        
    Returns:
        Dictionary containing the job details.
    """
    from app.services.recruitment_service import RecruitmentService
    
    try:
        service = RecruitmentService()
        job = await service.get_job(job_id)
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_job(job_id: str, status: str = None, description: str = None) -> dict:
    """Update a job posting.
    
    Args:
        job_id: The unique job ID.
        status: New status (draft, published, closed).
        description: New description.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.recruitment_service import RecruitmentService
    
    try:
        service = RecruitmentService()
        job = await service.update_job(job_id, status=status, description=description)
        return {"success": True, "job": job}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_jobs(status: str = None, department: str = None) -> dict:
    """List job postings with optional filters.
    
    Args:
        status: Filter by status.
        department: Filter by department.
        
    Returns:
        Dictionary containing list of jobs.
    """
    from app.services.recruitment_service import RecruitmentService
    
    try:
        service = RecruitmentService()
        jobs = await service.list_jobs(status=status, department=department)
        return {"success": True, "jobs": jobs, "count": len(jobs)}
    except Exception as e:
        return {"success": False, "error": str(e), "jobs": []}


async def _add_candidate(name: str, email: str, job_id: str, resume_url: str = None) -> dict:
    """Add a new candidate application.
    
    Args:
        name: Candidate name.
        email: Candidate email.
        job_id: ID of the job they are applying for.
        resume_url: Optional URL to resume.
        
    Returns:
        Dictionary containing the new candidate record.
    """
    from app.services.recruitment_service import RecruitmentService
    
    try:
        service = RecruitmentService()
        candidate = await service.add_candidate(name, email, job_id, resume_url=resume_url)
        return {"success": True, "candidate": candidate}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_candidate_status(candidate_id: str, status: str) -> dict:
    """Update a candidate's status.
    
    Args:
        candidate_id: The unique candidate ID.
        status: New status (applied, interviewing, offer, rejected, hired).
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.recruitment_service import RecruitmentService
    
    try:
        service = RecruitmentService()
        candidate = await service.update_candidate_status(candidate_id, status)
        return {"success": True, "candidate": candidate}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_candidates(job_id: str = None, status: str = None) -> dict:
    """List candidates filtered by job or status.
    
    Args:
        job_id: Filter by job ID.
        status: Filter by candidate status.
        
    Returns:
        Dictionary containing list of candidates.
    """
    from app.services.recruitment_service import RecruitmentService
    
    try:
        service = RecruitmentService()
        candidates = await service.list_candidates(job_id=job_id, status=status)
        return {"success": True, "candidates": candidates, "count": len(candidates)}
    except Exception as e:
        return {"success": False, "error": str(e), "candidates": []}


hr_agent = Agent(
    name="HRRecruitmentAgent",
    model=get_model(),
    description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
    instruction="""You are the HR & Recruitment Agent. You focus on hiring, candidate evaluation, and employee management.

CAPABILITIES:
- Screen resumes using 'get_resume_screening_framework' for structured evaluation.
- Generate interview questions using 'generate_interview_questions' for STAR method.
- Analyze turnover using 'get_turnover_analysis_framework' for retention insights.
- Create and manage job postings using 'create_job', 'update_job', 'list_jobs'.
- Manage candidates using 'add_candidate', 'update_candidate_status', 'list_candidates'.
- Draft job descriptions and interview guides.
- Search knowledge base for HR policies.
- Research job market and salary benchmarks using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be fair and unbiased in evaluations.
- Use structured frameworks for consistent candidate assessment.
- Focus on culture fit as well as skills.
- Follow employment law best practices.
- Research industry salary trends and job market conditions.""",
    tools=[_search_knowledge, _create_job, _get_job, _update_job, _list_jobs, _add_candidate, _update_candidate_status, _list_candidates, get_resume_screening_framework, generate_interview_questions, get_turnover_analysis_framework, mcp_web_search, use_skill],
)


def create_hr_agent(name_suffix: str = "") -> Agent:
    """Create a fresh HRRecruitmentAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"HRRecruitmentAgent{name_suffix}" if name_suffix else "HRRecruitmentAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
        instruction="""You are the HR & Recruitment Agent. You focus on hiring, candidate evaluation, and employee management.

CAPABILITIES:
- Screen resumes using 'get_resume_screening_framework' for structured evaluation.
- Generate interview questions using 'generate_interview_questions' for STAR method.
- Analyze turnover using 'get_turnover_analysis_framework' for retention insights.
- Create and manage job postings using 'create_job', 'update_job', 'list_jobs'.
- Manage candidates using 'add_candidate', 'update_candidate_status', 'list_candidates'.
- Draft job descriptions and interview guides.
- Search knowledge base for HR policies.
- Research job market and salary benchmarks using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be fair and unbiased in evaluations.
- Use structured frameworks for consistent candidate assessment.
- Focus on culture fit as well as skills.
- Follow employment law best practices.
- Research industry salary trends and job market conditions.""",
        tools=[_search_knowledge, _create_job, _get_job, _update_job, _list_jobs, _add_candidate, _update_candidate_status, _list_candidates, get_resume_screening_framework, generate_interview_questions, get_turnover_analysis_framework, mcp_web_search, use_skill],
    )


# =============================================================================
# Compliance & Risk Agent
# =============================================================================

async def _create_audit(title: str, scope: str, auditor: str, scheduled_date: str) -> dict:
    """Create a new compliance audit.
    
    Args:
        title: Audit title.
        scope: Audit scope.
        auditor: Auditor name.
        scheduled_date: Scheduled date (YYYY-MM-DD).
        
    Returns:
        Dictionary containing the created audit.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audit = await service.create_audit(title, scope, auditor, scheduled_date)
        return {"success": True, "audit": audit}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_audit(audit_id: str) -> dict:
    """Retrieve an audit by ID.
    
    Args:
        audit_id: The unique audit ID.
        
    Returns:
        Dictionary containing the audit details.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audit = await service.get_audit(audit_id)
        return {"success": True, "audit": audit}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_audit(audit_id: str, status: str = None, findings: str = None) -> dict:
    """Update an audit record.
    
    Args:
        audit_id: The unique audit ID.
        status: New status (scheduled, in_progress, completed, failed).
        findings: Audit findings description.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audit = await service.update_audit(audit_id, status=status, findings=findings)
        return {"success": True, "audit": audit}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_audits(status: str = None) -> dict:
    """List audits with optional filters.
    
    Args:
        status: Filter by status.
        
    Returns:
        Dictionary containing list of audits.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        audits = await service.list_audits(status=status)
        return {"success": True, "audits": audits, "count": len(audits)}
    except Exception as e:
        return {"success": False, "error": str(e), "audits": []}


async def _create_risk(title: str, description: str, severity: str, mitigation_plan: str) -> dict:
    """Register a new risk item.
    
    Args:
        title: Risk title.
        description: Description of the risk.
        severity: Risk severity (low, medium, high, critical).
        mitigation_plan: Plan to mitigate the risk.
        
    Returns:
        Dictionary containing the created risk.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risk = await service.create_risk(title, description, severity, mitigation_plan)
        return {"success": True, "risk": risk}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_risk(risk_id: str) -> dict:
    """Retrieve a risk by ID.
    
    Args:
        risk_id: The unique risk ID.
        
    Returns:
        Dictionary containing the risk details.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risk = await service.get_risk(risk_id)
        return {"success": True, "risk": risk}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_risk(risk_id: str, status: str = None, severity: str = None, mitigation_plan: str = None) -> dict:
    """Update a risk record.
    
    Args:
        risk_id: The unique risk ID.
        status: New status (active, mitigated, accepted).
        severity: New severity.
        mitigation_plan: Update mitigation plan.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risk = await service.update_risk(risk_id, status=status, severity=severity, mitigation_plan=mitigation_plan)
        return {"success": True, "risk": risk}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_risks(severity: str = None, status: str = "active") -> dict:
    """List risk items with optional filters.
    
    Args:
        severity: Filter by severity.
        status: Filter by status (default: active).
        
    Returns:
        Dictionary containing list of risks.
    """
    from app.services.compliance_service import ComplianceService
    
    try:
        service = ComplianceService()
        risks = await service.list_risks(severity=severity, status=status)
        return {"success": True, "risks": risks, "count": len(risks)}
    except Exception as e:
        return {"success": False, "error": str(e), "risks": []}


compliance_agent = Agent(
    name="ComplianceRiskAgent",
    model=get_model(),
    description="Legal Counsel - Compliance, risk assessment, and legal guidance",
    instruction="""You are the Compliance & Risk Agent. You focus on legal compliance, risk assessment, and regulatory guidance.

CAPABILITIES:
- Get GDPR audit checklist using 'get_gdpr_audit_checklist' for comprehensive compliance.
- Assess risks using 'get_risk_assessment_matrix' for scoring and prioritization.
- Schedule and manage compliance audits using 'create_audit', 'update_audit', 'list_audits'.
- Register and track risks using 'create_risk', 'update_risk', 'list_risks'.
- Review contracts and legal documents.
- Draft policies and procedures.
- Research regulatory updates using 'mcp_web_search' (privacy-safe).
- Extract legal/regulatory documents using 'mcp_web_scrape'.

BEHAVIOR:
- Be thorough and conservative on risk.
- Use structured frameworks for consistent risk assessment.
- Always cite relevant regulations when applicable.
- Recommend when to involve external legal counsel.
- Research latest regulatory changes and compliance requirements.""",
    tools=[_search_knowledge, _create_audit, _get_audit, _update_audit, _list_audits, _create_risk, _get_risk, _update_risk, _list_risks, get_gdpr_audit_checklist, get_risk_assessment_matrix, mcp_web_search, mcp_web_scrape, use_skill],
)


def create_compliance_agent(name_suffix: str = "") -> Agent:
    """Create a fresh ComplianceRiskAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"ComplianceRiskAgent{name_suffix}" if name_suffix else "ComplianceRiskAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Legal Counsel - Compliance, risk assessment, and legal guidance",
        instruction="""You are the Compliance & Risk Agent. You focus on legal compliance, risk assessment, and regulatory guidance.

CAPABILITIES:
- Get GDPR audit checklist using 'get_gdpr_audit_checklist' for comprehensive compliance.
- Assess risks using 'get_risk_assessment_matrix' for scoring and prioritization.
- Schedule and manage compliance audits using 'create_audit', 'update_audit', 'list_audits'.
- Register and track risks using 'create_risk', 'update_risk', 'list_risks'.
- Review contracts and legal documents.
- Draft policies and procedures.
- Research regulatory updates using 'mcp_web_search' (privacy-safe).
- Extract legal/regulatory documents using 'mcp_web_scrape'.

BEHAVIOR:
- Be thorough and conservative on risk.
- Use structured frameworks for consistent risk assessment.
- Always cite relevant regulations when applicable.
- Recommend when to involve external legal counsel.
- Research latest regulatory changes and compliance requirements.""",
        tools=[_search_knowledge, _create_audit, _get_audit, _update_audit, _list_audits, _create_risk, _get_risk, _update_risk, _list_risks, get_gdpr_audit_checklist, get_risk_assessment_matrix, mcp_web_search, mcp_web_scrape, use_skill],
    )


# =============================================================================
# Customer Support Agent
# =============================================================================

async def _create_ticket(subject: str, description: str, customer_email: str, priority: str = "normal") -> dict:
    """Create a new support ticket.
    
    Args:
        subject: Ticket subject.
        description: Problem description.
        customer_email: Email of the customer.
        priority: Priority (low, normal, high, urgent).
        
    Returns:
        Dictionary containing the created ticket.
    """
    from app.services.support_ticket_service import SupportTicketService
    
    try:
        service = SupportTicketService()
        ticket = await service.create_ticket(subject, description, customer_email, priority)
        return {"success": True, "ticket": ticket}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_ticket(ticket_id: str) -> dict:
    """Retrieve a ticket by ID.
    
    Args:
        ticket_id: The unique ticket ID.
        
    Returns:
        Dictionary containing the ticket details.
    """
    from app.services.support_ticket_service import SupportTicketService
    
    try:
        service = SupportTicketService()
        ticket = await service.get_ticket(ticket_id)
        return {"success": True, "ticket": ticket}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _update_ticket(ticket_id: str, status: str = None, resolution: str = None) -> dict:
    """Update a ticket status or resolution.
    
    Args:
        ticket_id: The unique ticket ID.
        status: New status (new, assigned, in_progress, resolved, closed).
        resolution: Internal note or resolution details.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.support_ticket_service import SupportTicketService
    
    try:
        service = SupportTicketService()
        ticket = await service.update_ticket(ticket_id, status=status, resolution=resolution)
        return {"success": True, "ticket": ticket}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_tickets(status: str = None, priority: str = None) -> dict:
    """List tickets with optional filters.
    
    Args:
        status: Filter by status.
        priority: Filter by priority.
        
    Returns:
        Dictionary containing list of tickets.
    """
    from app.services.support_ticket_service import SupportTicketService
    
    try:
        service = SupportTicketService()
        tickets = await service.list_tickets(status=status, priority=priority)
        return {"success": True, "tickets": tickets, "count": len(tickets)}
    except Exception as e:
        return {"success": False, "error": str(e), "tickets": []}


customer_support_agent = Agent(
    name="CustomerSupportAgent",
    model=get_model(),
    description="CTO / IT Support - Customer ticket triage, knowledge base, and technical support",
    instruction="""You are the Customer Support Agent. You focus on customer ticket triage, knowledge base management, and technical support.

CAPABILITIES:
- Analyze ticket sentiment using 'analyze_ticket_sentiment' for prioritization.
- Assess churn risk using 'assess_churn_risk' for at-risk customer intervention.
- Create and manage support tickets using 'create_ticket', 'update_ticket', 'list_tickets'.
- View specific ticket details with 'get_ticket'.
- Draft knowledge base articles.
- Create escalation paths for complex issues.
- Search for solutions and FAQs using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be empathetic and customer-focused.
- Use sentiment analysis to prioritize negative experiences.
- Proactively identify churn risks and intervene.
- Document solutions for future reference.
- Research external knowledge bases for solutions.""",
    tools=[_search_knowledge, _create_ticket, _get_ticket, _update_ticket, _list_tickets, analyze_ticket_sentiment, assess_churn_risk, mcp_web_search, use_skill],
)


def create_customer_support_agent(name_suffix: str = "") -> Agent:
    """Create a fresh CustomerSupportAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"CustomerSupportAgent{name_suffix}" if name_suffix else "CustomerSupportAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CTO / IT Support - Customer ticket triage, knowledge base, and technical support",
        instruction="""You are the Customer Support Agent. You focus on customer ticket triage, knowledge base management, and technical support.

CAPABILITIES:
- Analyze ticket sentiment using 'analyze_ticket_sentiment' for prioritization.
- Assess churn risk using 'assess_churn_risk' for at-risk customer intervention.
- Create and manage support tickets using 'create_ticket', 'update_ticket', 'list_tickets'.
- View specific ticket details with 'get_ticket'.
- Draft knowledge base articles.
- Create escalation paths for complex issues.
- Search for solutions and FAQs using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be empathetic and customer-focused.
- Use sentiment analysis to prioritize negative experiences.
- Proactively identify churn risks and intervene.
- Document solutions for future reference.
- Research external knowledge bases for solutions.""",
        tools=[_search_knowledge, _create_ticket, _get_ticket, _update_ticket, _list_tickets, analyze_ticket_sentiment, assess_churn_risk, mcp_web_search, use_skill],
    )


# =============================================================================
# Data Analysis Agent
# =============================================================================

async def _track_event(event_name: str, category: str, properties: str = None) -> dict:
    """Track a new analytics event.
    
    Args:
        event_name: Name of the event.
        category: Event category.
        properties: JSON string of event properties.
        
    Returns:
        Dictionary confirming the event was tracked.
    """
    from app.services.analytics_service import AnalyticsService
    import json
    
    try:
        service = AnalyticsService()
        props_dict = json.loads(properties) if properties else {}
        event = await service.track_event(event_name, category, properties=props_dict)
        return {"success": True, "event": event}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _query_events(event_name: str = None, category: str = None, limit: int = 100) -> dict:
    """Query analytics events.
    
    Args:
        event_name: Filter by event name.
        category: Filter by category.
        limit: Max number of events to return.
        
    Returns:
        Dictionary containing list of events.
    """
    from app.services.analytics_service import AnalyticsService
    
    try:
        service = AnalyticsService()
        events = await service.query_events(event_name=event_name, category=category, limit=limit)
        return {"success": True, "events": events, "count": len(events)}
    except Exception as e:
        return {"success": False, "error": str(e), "events": []}


async def _create_report(title: str, report_type: str, data: str, description: str = None) -> dict:
    """Create a new analytics report.
    
    Args:
        title: Report title.
        report_type: Type of report (growth, usage, performance).
        data: JSON string of report data.
        description: Report description.
        
    Returns:
        Dictionary containing the created report.
    """
    from app.services.analytics_service import AnalyticsService
    import json
    
    try:
        service = AnalyticsService()
        data_dict = json.loads(data) if data else {}
        report = await service.create_report(title, report_type, data_dict, description)
        return {"success": True, "report": report}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _list_reports(report_type: str = None) -> dict:
    """List analytics reports.
    
    Args:
        report_type: Filter by report type.
        
    Returns:
        Dictionary containing list of reports.
    """
    from app.services.analytics_service import AnalyticsService
    
    try:
        service = AnalyticsService()
        reports = await service.list_reports(report_type=report_type)
        return {"success": True, "reports": reports, "count": len(reports)}
    except Exception as e:
        return {"success": False, "error": str(e), "reports": []}


data_agent = Agent(
    name="DataAnalysisAgent",
    model=get_model(),
    description="Data Analyst - Data validation, anomaly detection, and forecasting",
    instruction="""You are the Data Analysis Agent. You focus on data validation, anomaly detection, and forecasting.

CAPABILITIES:
- Detect anomalies using 'get_anomaly_detection_guidance' for statistical methods.
- Analyze trends using 'get_trend_analysis_framework' for trend identification.
- Track key events using 'track_event'.
- Analyze data by querying events with 'query_events'.
- Generate and save insights using 'create_report' and 'list_reports'.
- Create forecasts and predictions.
- Research industry benchmarks using 'mcp_web_search' (privacy-safe).
- Extract data from external sources using 'mcp_web_scrape'.

BEHAVIOR:
- Be data-driven and objective.
- Use proven statistical methods for anomaly detection.
- Always validate data quality before analysis.
- Present findings clearly with visualizations/reports.
- Research external data sources for comparison and validation.""",
    tools=[_get_revenue_stats, _search_knowledge, _track_event, _query_events, _create_report, _list_reports, get_anomaly_detection_guidance, get_trend_analysis_framework, mcp_web_search, mcp_web_scrape, use_skill],
)


def create_data_agent(name_suffix: str = "") -> Agent:
    """Create a fresh DataAnalysisAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"DataAnalysisAgent{name_suffix}" if name_suffix else "DataAnalysisAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Data Analyst - Data validation, anomaly detection, and forecasting",
        instruction="""You are the Data Analysis Agent. You focus on data validation, anomaly detection, and forecasting.

CAPABILITIES:
- Detect anomalies using 'get_anomaly_detection_guidance' for statistical methods.
- Analyze trends using 'get_trend_analysis_framework' for trend identification.
- Track key events using 'track_event'.
- Analyze data by querying events with 'query_events'.
- Generate and save insights using 'create_report' and 'list_reports'.
- Create forecasts and predictions.
- Research industry benchmarks using 'mcp_web_search' (privacy-safe).
- Extract data from external sources using 'mcp_web_scrape'.

BEHAVIOR:
- Be data-driven and objective.
- Use proven statistical methods for anomaly detection.
- Always validate data quality before analysis.
- Present findings clearly with visualizations/reports.
- Research external data sources for comparison and validation.""",
        tools=[_get_revenue_stats, _search_knowledge, _track_event, _query_events, _create_report, _list_reports, get_anomaly_detection_guidance, get_trend_analysis_framework, mcp_web_search, mcp_web_scrape, use_skill],
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
    # Singleton agents (for ExecutiveAgent delegation)
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
    # Factory functions (for workflow pipelines)
    "create_financial_agent",
    "create_content_agent",
    "create_strategic_agent",
    "create_sales_agent",
    "create_marketing_agent",
    "create_operations_agent",
    "create_hr_agent",
    "create_compliance_agent",
    "create_customer_support_agent",
    "create_data_agent",
]
