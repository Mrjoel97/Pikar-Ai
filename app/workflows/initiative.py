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

"""Initiative & Project Lifecycle Workflows (Category 1).

This module implements 6 workflow agents for initiative lifecycle management:
1. InitiativeIdeationPipeline - Brainstorm and validate initiative ideas
2. InitiativeValidationPipeline - Multi-perspective feasibility analysis
3. InitiativeBuildPipeline - Plan resources and execution timeline
4. InitiativeTestPipeline - Iterative quality and compliance check
5. InitiativeLaunchPipeline - Coordinated go-to-market execution
6. InitiativeScalePipeline - Growth optimization post-launch

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

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
)


# =============================================================================
# 1. InitiativeIdeationPipeline
# =============================================================================

InitiativeIdeationPipeline = SequentialAgent(
    name="InitiativeIdeationPipeline",
    description="Brainstorm and validate initiative ideas through strategic, content, and data analysis",
    sub_agents=[strategic_agent, content_agent, data_agent],
)


# =============================================================================
# 2. InitiativeValidationPipeline
# =============================================================================

# Parallel analysis phase - Executive synthesizes results externally
_validation_parallel = ParallelAgent(
    name="ValidationParallelAnalysis",
    description="Concurrent multi-perspective feasibility analysis",
    sub_agents=[data_agent, financial_agent, strategic_agent],
)

InitiativeValidationPipeline = SequentialAgent(
    name="InitiativeValidationPipeline",
    description="Multi-perspective feasibility analysis with parallel data gathering",
    sub_agents=[_validation_parallel],
)


# =============================================================================
# 3. InitiativeBuildPipeline
# =============================================================================

InitiativeBuildPipeline = SequentialAgent(
    name="InitiativeBuildPipeline",
    description="Plan resources and execution timeline for an initiative",
    sub_agents=[strategic_agent, operations_agent, hr_agent],
)


# =============================================================================
# 4. InitiativeTestPipeline
# =============================================================================

# Quality check loop - iterates until compliance and quality pass
_test_sequential = SequentialAgent(
    name="TestQualityCheck",
    description="Single iteration of quality and compliance verification",
    sub_agents=[operations_agent, data_agent, compliance_agent],
)

InitiativeTestPipeline = LoopAgent(
    name="InitiativeTestPipeline",
    description="Iterative quality and compliance check until all criteria pass",
    sub_agents=[_test_sequential],
    max_iterations=5,
)


# =============================================================================
# 5. InitiativeLaunchPipeline
# =============================================================================

# Parallel launch preparation - Executive coordinates externally
_launch_parallel = ParallelAgent(
    name="LaunchParallelPrep",
    description="Concurrent go-to-market preparation across marketing, sales, and content",
    sub_agents=[marketing_agent, sales_agent, content_agent],
)

InitiativeLaunchPipeline = SequentialAgent(
    name="InitiativeLaunchPipeline",
    description="Coordinated go-to-market execution with parallel preparation",
    sub_agents=[_launch_parallel],
)


# =============================================================================
# 6. InitiativeScalePipeline
# =============================================================================

InitiativeScalePipeline = SequentialAgent(
    name="InitiativeScalePipeline",
    description="Growth optimization post-launch through data-driven financial and strategic analysis",
    sub_agents=[data_agent, financial_agent, strategic_agent, operations_agent],
)


# =============================================================================
# Exports
# =============================================================================

INITIATIVE_WORKFLOWS = [
    InitiativeIdeationPipeline,
    InitiativeValidationPipeline,
    InitiativeBuildPipeline,
    InitiativeTestPipeline,
    InitiativeLaunchPipeline,
    InitiativeScalePipeline,
]

__all__ = [
    "InitiativeIdeationPipeline",
    "InitiativeValidationPipeline",
    "InitiativeBuildPipeline",
    "InitiativeTestPipeline",
    "InitiativeLaunchPipeline",
    "InitiativeScalePipeline",
    "INITIATIVE_WORKFLOWS",
]
