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

"""Pikar AI Executive Agent - Central Orchestrator for Business Operations.

This module implements the Executive Agent, which serves as the primary
interface for users and orchestrates tasks across specialized agents.
"""

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import uuid

# Import specialized agents for sub_agents hierarchy
from app.agents.specialized_agents import SPECIALIZED_AGENTS

# Configure Vertex AI
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "my-project-pk-484623")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


# =============================================================================
# Global Business Tools
# =============================================================================

def get_revenue_stats() -> dict:
    """Provides current revenue statistics and financial health metrics.
    
    Returns:
        Dictionary containing revenue data, trends, and financial KPIs.
    """
    # In production, this would query the database
    return {
        "revenue": 1000.0,
        "currency": "USD",
        "period": "current_month",
        "trend": "stable"
    }


def search_business_knowledge(query: str) -> dict:
    """Search the Knowledge Vault for relevant business information.
    
    This tool queries the RAG system to find context and information
    about the business, products, customers, and historical decisions.
    
    Args:
        query: The search query to find relevant business knowledge.
        
    Returns:
        Dictionary containing search results with relevant context.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge
        return search_knowledge(query, top_k=5)
    except Exception as e:
        # Fallback for when Knowledge Vault is not configured
        return {"results": [], "query": query, "note": "Knowledge Vault not configured"}


def update_initiative_status(initiative_id: str, status: str) -> dict:
    """Updates the status of a business initiative or project.
    
    Args:
        initiative_id: The unique identifier of the initiative.
        status: The new status (e.g., 'in_progress', 'completed', 'blocked').
        
    Returns:
        Dictionary confirming the update.
    """
    print(f"Updating initiative {initiative_id} to {status}")
    return {"success": True, "initiative_id": initiative_id, "new_status": status}


def create_task(description: str, assignee: str, priority: str) -> dict:
    """Creates a new task in the task management system.
    
    Args:
        description: Clear description of what needs to be done.
        assignee: Who should work on this task (use 'unassigned' if no specific person).
        priority: Task priority - must be one of: low, medium, high, urgent.
        
    Returns:
        Dictionary with the created task details including task_id, description,
        assignee, priority, and status.
    """
    task_id = str(uuid.uuid4())
    print(f"Created task '{description}' with id {task_id}")
    return {
        "task_id": task_id,
        "description": description,
        "assignee": assignee,
        "priority": priority,
        "status": "created"
    }


# NOTE: Orchestration tools removed - ADK handles delegation natively via sub_agents


# =============================================================================
# Executive Agent Definition
# =============================================================================

EXECUTIVE_INSTRUCTION = """You are the Executive Agent for Pikar AI - the Chief of Staff and Central Orchestrator.

## YOUR ROLE
You are the primary interface between the user and Pikar AI's multi-agent ecosystem. You oversee all business operations and coordinate specialized agents to accomplish complex tasks.

## CAPABILITIES
1. **Business Intelligence**: Monitor business health using 'get_revenue_stats'
2. **Knowledge Access**: Search the Knowledge Vault using 'search_business_knowledge' for context and history
3. **Project Management**: Track initiatives with 'update_initiative_status' and create tasks with 'create_task'
4. **Agent Delegation**: You have specialized sub-agents that you can delegate to naturally (the system handles routing automatically)

## BEHAVIOR GUIDELINES
- Be concise, strategic, and decisive
- ALWAYS check 'search_business_knowledge' before asking the user for context
- When tasks require domain expertise, describe what needs to be done and the appropriate specialist will be invoked
- Provide clear summaries of work and next steps
- Think like a Chief of Staff - anticipate needs and coordinate effectively

## AVAILABLE SPECIALISTS (Sub-Agents)
The following specialists are available for delegation:
- FinancialAnalysisAgent: Revenue, costs, forecasting, financial health
- ContentCreationAgent: Marketing copy, blog posts, social media content
- StrategicPlanningAgent: OKRs, long-term goals, initiative tracking
- SalesIntelligenceAgent: Deal scoring, lead analysis, sales enablement
- MarketingAutomationAgent: Campaigns, content scheduling, audience targeting
- OperationsOptimizationAgent: Process improvement, efficiency, rollout planning
- HRRecruitmentAgent: Hiring, candidate evaluation, onboarding
- ComplianceRiskAgent: Legal compliance, risk assessment, regulatory guidance
- CustomerSupportAgent: Ticket triage, knowledge base, support metrics
- DataAnalysisAgent: Data validation, anomaly detection, forecasting

Simply describe the task and the system will route to the appropriate specialist.
"""

executive_agent = Agent(
    name="ExecutiveAgent",
    model=Gemini(
        model="gemini-1.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Chief of Staff / Central Orchestrator - Primary interface for Pikar AI users",
    instruction=EXECUTIVE_INSTRUCTION,
    tools=[
        # Business tools
        get_revenue_stats,
        search_business_knowledge,
        update_initiative_status,
        create_task,
    ],
    # Native ADK sub_agents hierarchy - delegation handled automatically
    sub_agents=SPECIALIZED_AGENTS,
)

# Create the application
app = App(root_agent=executive_agent, name="app")
