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

"""Dynamic Workflow Generator - Custom BaseAgent for Runtime Workflow Creation.

This module implements the DynamicWorkflowGenerator, a custom BaseAgent that
analyzes user requests and dynamically composes workflows from available
specialized agents.

Note: Executive Agent handles final synthesis externally per Agent-Eco-System.md.
"""

from typing import AsyncGenerator
from google.adk.agents import BaseAgent, SequentialAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from app.agents.specialized_agents import (
    strategic_agent,
    content_agent,
    data_agent,
    financial_agent,
    operations_agent,
    hr_agent,
    marketing_agent,
    sales_agent,
    compliance_agent,
    customer_support_agent,
)


# Agent registry for dynamic lookup
AGENT_REGISTRY = {
    "strategic": strategic_agent,
    "content": content_agent,
    "data": data_agent,
    "financial": financial_agent,
    "operations": operations_agent,
    "hr": hr_agent,
    "marketing": marketing_agent,
    "sales": sales_agent,
    "compliance": compliance_agent,
    "support": customer_support_agent,
}


class DynamicWorkflowGenerator(BaseAgent):
    """Dynamically creates and executes workflows based on user requests.
    
    This agent analyzes the user's intent and dynamically composes a workflow
    from available specialized agents using the appropriate pattern:
    - Sequential: For step-by-step processes
    - Parallel: For concurrent data gathering
    
    The workflow is created at runtime and executed immediately.
    Executive Agent handles final synthesis externally.
    """
    
    def __init__(self):
        super().__init__(
            name="DynamicWorkflowGenerator",
            description="Analyzes user requests and creates custom workflows dynamically",
        )
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Analyze request and create a dynamic workflow.
        
        Args:
            ctx: The invocation context containing session state and history.
            
        Yields:
            Events produced during workflow execution.
        """
        # Get the user's request from session state
        user_request = ctx.session.state.get("user_request", "")
        
        if not user_request:
            # No request in state, check recent messages
            if ctx.session.events:
                for event in reversed(ctx.session.events):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                user_request = part.text
                                break
                    if user_request:
                        break
        
        # Analyze intent to determine agents needed
        agents_needed = self._analyze_intent(user_request)
        pattern = self._determine_pattern(user_request, agents_needed)
        
        # Build the dynamic workflow
        workflow = self._build_workflow(agents_needed, pattern, user_request)
        
        # Store workflow info in state for transparency
        ctx.session.state["dynamic_workflow"] = {
            "agents": [a.name for a in agents_needed],
            "pattern": pattern,
            "request": user_request,
        }
        
        # Execute the workflow if we have agents
        if workflow:
            async for event in workflow.run_async(ctx):
                yield event
        else:
            # No suitable agents found, return informative message
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(
                        text=f"I analyzed your request but couldn't determine the right specialists. "
                             f"Available specialists: {', '.join(AGENT_REGISTRY.keys())}. "
                             f"Please rephrase your request or specify which area you need help with."
                    )]
                ),
                actions=EventActions(),
            )
    
    def _analyze_intent(self, request: str) -> list:
        """Analyze the request to determine which agents are needed.
        
        Args:
            request: The user's request text.
            
        Returns:
            List of agents needed for this request.
        """
        request_lower = request.lower()
        agents = []
        
        # Keyword mapping to agents
        keyword_map = {
            "financial": ["financial", "revenue", "cost", "budget", "profit", "money", "pricing"],
            "strategic": ["strategy", "plan", "goal", "objective", "okr", "initiative"],
            "data": ["data", "analysis", "metrics", "kpi", "dashboard", "analytics"],
            "content": ["content", "blog", "article", "write", "copy", "newsletter"],
            "marketing": ["marketing", "campaign", "email", "social", "brand", "advertising"],
            "sales": ["sales", "lead", "deal", "crm", "outreach", "pipeline"],
            "hr": ["hr", "hiring", "recruit", "employee", "onboard", "training", "performance"],
            "operations": ["operations", "process", "efficiency", "rollout", "workflow"],
            "compliance": ["compliance", "legal", "risk", "policy", "audit", "gdpr"],
            "support": ["support", "customer", "ticket", "help desk", "service"],
        }
        
        for agent_key, keywords in keyword_map.items():
            for keyword in keywords:
                if keyword in request_lower:
                    if AGENT_REGISTRY[agent_key] not in agents:
                        agents.append(AGENT_REGISTRY[agent_key])
                    break
        
        # Default to strategic + data if no specific agents identified
        if not agents:
            agents = [strategic_agent, data_agent]
        
        return agents
    
    def _determine_pattern(self, request: str, agents: list) -> str:
        """Determine the best workflow pattern for the request.
        
        Args:
            request: The user's request text.
            agents: List of agents identified.
            
        Returns:
            Pattern name: 'sequential' or 'parallel'.
        """
        request_lower = request.lower()
        
        # Parallel pattern indicators
        if any(word in request_lower for word in ["compare", "simultaneously", "all perspectives", "consensus"]):
            return "parallel"
        
        # Default to sequential for most use cases
        return "sequential"
    
    def _build_workflow(self, agents: list, pattern: str, request: str):
        """Build a workflow agent from the determined agents and pattern.
        
        Args:
            agents: List of agents to include.
            pattern: The pattern to use ('sequential' or 'parallel').
            request: The original request for naming.
            
        Returns:
            A workflow agent instance, or None if no agents.
        """
        if not agents:
            return None
        
        workflow_name = f"DynamicWorkflow_{len(agents)}agents"
        
        if pattern == "parallel":
            return ParallelAgent(
                name=workflow_name,
                description=f"Dynamic parallel workflow for: {request[:50]}...",
                sub_agents=agents,
            )
        else:  # sequential
            return SequentialAgent(
                name=workflow_name,
                description=f"Dynamic sequential workflow for: {request[:50]}...",
                sub_agents=agents,
            )


# Singleton instance
dynamic_workflow_generator = DynamicWorkflowGenerator()

__all__ = [
    "DynamicWorkflowGenerator",
    "dynamic_workflow_generator",
    "AGENT_REGISTRY",
]
