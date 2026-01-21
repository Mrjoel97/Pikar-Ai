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

"""Documentation & Reporting Workflows (Category 9).

This module implements 5 workflow agents for documentation:
45. BusinessDocumentationPipeline - Business process documentation
46. ProjectDocumentationPipeline - Project documentation
47. ReportCreationPipeline - Custom report generation
48. BoardPresentationPipeline - Board meeting preparation
49. WeeklyBriefingPipeline - Automated weekly executive brief

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, ParallelAgent

from app.agents.specialized_agents import (
    strategic_agent,
    content_agent,
    data_agent,
    financial_agent,
    operations_agent,
    compliance_agent,
)


# =============================================================================
# 45. BusinessDocumentationPipeline
# =============================================================================

BusinessDocumentationPipeline = SequentialAgent(
    name="BusinessDocumentationPipeline",
    description="Business process documentation with compliance review",
    sub_agents=[strategic_agent, content_agent, compliance_agent],
)


# =============================================================================
# 46. ProjectDocumentationPipeline
# =============================================================================

ProjectDocumentationPipeline = SequentialAgent(
    name="ProjectDocumentationPipeline",
    description="Project documentation from operations to content to data",
    sub_agents=[operations_agent, content_agent, data_agent],
)


# =============================================================================
# 47. ReportCreationPipeline
# =============================================================================

_report_data_parallel = ParallelAgent(
    name="ReportDataGathering",
    description="Parallel data gathering from data and financial sources",
    sub_agents=[data_agent, financial_agent],
)

ReportCreationPipeline = SequentialAgent(
    name="ReportCreationPipeline",
    description="Custom report generation with parallel data gathering",
    sub_agents=[_report_data_parallel, content_agent],
)


# =============================================================================
# 48. BoardPresentationPipeline
# =============================================================================

_board_parallel = ParallelAgent(
    name="BoardPresentationGathering",
    description="Parallel board presentation content from data, financial, and strategic",
    sub_agents=[data_agent, financial_agent, strategic_agent],
)

BoardPresentationPipeline = SequentialAgent(
    name="BoardPresentationPipeline",
    description="Board meeting preparation with parallel analysis",
    sub_agents=[_board_parallel],
)


# =============================================================================
# 49. WeeklyBriefingPipeline
# =============================================================================

WeeklyBriefingPipeline = SequentialAgent(
    name="WeeklyBriefingPipeline",
    description="Automated weekly executive brief generation",
    sub_agents=[data_agent, strategic_agent],
)


# =============================================================================
# Exports
# =============================================================================

DOCUMENTATION_WORKFLOWS = [
    BusinessDocumentationPipeline,
    ProjectDocumentationPipeline,
    ReportCreationPipeline,
    BoardPresentationPipeline,
    WeeklyBriefingPipeline,
]

__all__ = [
    "BusinessDocumentationPipeline",
    "ProjectDocumentationPipeline",
    "ReportCreationPipeline",
    "BoardPresentationPipeline",
    "WeeklyBriefingPipeline",
    "DOCUMENTATION_WORKFLOWS",
]
