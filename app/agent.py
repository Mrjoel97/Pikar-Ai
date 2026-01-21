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


def create_task(description: str, assignee: str = None, priority: str = "medium") -> dict:
    """Creates a new task in the task management system.
    
    Args:
        description: Clear description of what needs to be done.
        assignee: Optional - who should work on this task.
        priority: Task priority (low, medium, high, urgent).
        
    Returns:
        Dictionary with the created task details.
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


# =============================================================================
# Orchestration Tools
# =============================================================================

def get_available_agents() -> dict:
    """Get list of all specialized agents available for delegation.
    
    Use this to understand which agents are available and their capabilities
    before delegating a task.
    
    Returns:
        Dictionary containing list of agents with names and roles.
    """
    from app.orchestration.tools import get_available_agents as _get_agents
    return _get_agents()


def delegate_to_agent(agent_name: str, task_description: str) -> dict:
    """Delegate a specific task to a specialized agent.
    
    Use this when a task is better handled by a specialist:
    - Financial Analysis Agent: Revenue analysis, forecasting, financial health
    - Content Creation Agent: Marketing copy, blog posts, social media
    - Strategic Planning Agent: OKRs, long-term goals, initiatives
    - Sales Intelligence Agent: Deal scoring, lead analysis, outreach
    - Marketing Automation Agent: Campaigns, audience targeting
    - Operations Optimization Agent: Process improvement, efficiency
    - HR & Recruitment Agent: Hiring, candidate evaluation
    - Compliance & Risk Agent: Legal guidance, audit, risk assessment
    - Customer Support Agent: Ticket triage, knowledge base
    - Data Analysis Agent: Data validation, anomaly detection, forecasting
    
    Args:
        agent_name: Name of the specialized agent (e.g., "Financial Analysis Agent").
        task_description: Clear description of what the agent should do.
        
    Returns:
        Dictionary with delegation status.
    """
    from app.orchestration.tools import delegate_to_agent as _delegate
    return _delegate(agent_name, task_description)


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
4. **Agent Orchestration**: View available agents with 'get_available_agents' and delegate using 'delegate_to_agent'

## BEHAVIOR GUIDELINES
- Be concise, strategic, and decisive
- ALWAYS check 'search_business_knowledge' before asking the user for context
- Delegate to specialized agents when tasks require domain expertise
- Provide clear summaries of delegated work and next steps
- Think like a Chief of Staff - anticipate needs and coordinate effectively

## DELEGATION RULES
Before handling a request yourself, consider if a specialist would be better:
- Financial questions → Financial Analysis Agent
- Content creation → Content Creation Agent  
- Strategic planning → Strategic Planning Agent
- Sales tasks → Sales Intelligence Agent
- Marketing campaigns → Marketing Automation Agent
- Operations/efficiency → Operations Optimization Agent
- HR/hiring → HR & Recruitment Agent
- Legal/compliance → Compliance & Risk Agent
- Support tickets → Customer Support Agent
- Data analysis → Data Analysis Agent
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
        # Orchestration tools
        get_available_agents,
        delegate_to_agent,
    ],
)

# Create the application
app = App(root_agent=executive_agent, name="app")
