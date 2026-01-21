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

"""Goal Setting & Monitoring Workflows (Category 5).

This module implements 4 workflow agents for goal management:
27. OKRCreationPipeline - Create objectives and key results
28. GoalTrackingPipeline - Continuous goal progress monitoring
29. KPIDashboardPipeline - Real-time KPI aggregation
30. QuarterlyReviewPipeline - Quarterly business review

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

from app.agents.specialized_agents import (
    strategic_agent,
    data_agent,
    financial_agent,
    sales_agent,
)


# =============================================================================
# 27. OKRCreationPipeline
# =============================================================================

OKRCreationPipeline = SequentialAgent(
    name="OKRCreationPipeline",
    description="Create objectives and key results through strategic and data analysis",
    sub_agents=[strategic_agent, data_agent],
)


# =============================================================================
# 28. GoalTrackingPipeline
# =============================================================================

_goal_tracking_cycle = SequentialAgent(
    name="GoalTrackingCycle",
    description="Single iteration of goal progress monitoring",
    sub_agents=[data_agent, strategic_agent],
)

GoalTrackingPipeline = LoopAgent(
    name="GoalTrackingPipeline",
    description="Continuous goal progress monitoring with weekly iterations",
    sub_agents=[_goal_tracking_cycle],
    max_iterations=12,  # Quarterly tracking (12 weeks)
)


# =============================================================================
# 29. KPIDashboardPipeline
# =============================================================================

_kpi_parallel = ParallelAgent(
    name="KPIDataGathering",
    description="Parallel KPI data collection from multiple sources",
    sub_agents=[data_agent, financial_agent, sales_agent],
)

KPIDashboardPipeline = SequentialAgent(
    name="KPIDashboardPipeline",
    description="Real-time KPI aggregation with parallel data gathering",
    sub_agents=[_kpi_parallel],
)


# =============================================================================
# 30. QuarterlyReviewPipeline
# =============================================================================

QuarterlyReviewPipeline = SequentialAgent(
    name="QuarterlyReviewPipeline",
    description="Quarterly business review through comprehensive analysis",
    sub_agents=[data_agent, financial_agent, strategic_agent],
)


# =============================================================================
# Exports
# =============================================================================

GOALS_WORKFLOWS = [
    OKRCreationPipeline,
    GoalTrackingPipeline,
    KPIDashboardPipeline,
    QuarterlyReviewPipeline,
]

__all__ = [
    "OKRCreationPipeline",
    "GoalTrackingPipeline",
    "KPIDashboardPipeline",
    "QuarterlyReviewPipeline",
    "GOALS_WORKFLOWS",
]
