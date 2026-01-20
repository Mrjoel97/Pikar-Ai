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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth
import uuid

os.environ["GOOGLE_CLOUD_PROJECT"] = "my-project-pk-484623"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


def get_revenue_stats() -> dict:
    """Provides revenue statistics."""
    return {"revenue": 1000.0}

def search_business_knowledge(query: str) -> dict:
    """Searches for business knowledge."""
    return {"results": []}

def update_initiative_status(initiative_id: str, status: str) -> dict:
    """Updates the status of an initiative."""
    # In a real implementation, this would update a database.
    print(f"Updating initiative {initiative_id} to {status}")
    return {"success": True}

def create_task(description: str) -> dict:
    """Creates a new task."""
    # In a real implementation, this would create a task in a database.
    task_id = str(uuid.uuid4())
    print(f"Created task '{description}' with id {task_id}")
    return {"task_id": task_id}


executive_agent = Agent(
    name="ExecutiveAgent",
    model=Gemini(
        model="gemini-1.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Chief of Staff / Central Orchestrator",
    instruction="""You are the Executive Agent for Pikar AI. Your goal is to oversee the user's entire business operation.
    
    CAPABILITIES:
    - You act as the primary interface for the user.
    - Monitor business health using 'get_revenue_stats'.
    - Keep projects on track using 'update_initiative_status' and 'create_task'.
    
    BEHAVIOR:
    - Be concise, strategic, and decisive. 
    - Always check 'search_business_knowledge' before asking the user for context.""",
    tools=[get_revenue_stats, search_business_knowledge, update_initiative_status, create_task],
)

app = App(root_agent=executive_agent, name="app")
