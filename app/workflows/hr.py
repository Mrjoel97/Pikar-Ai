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

"""Team & HR Workflows (Category 8).

This module implements 4 workflow agents for HR operations:
41. TeamTrainingPipeline - Training program creation
42. RecruitmentPipeline - End-to-end hiring workflow
43. OnboardingPipeline - New employee onboarding
44. PerformanceReviewPipeline - Employee performance analysis

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent

from app.agents.specialized_agents import (
    content_agent,
    data_agent,
    operations_agent,
    hr_agent,
)


# =============================================================================
# 41. TeamTrainingPipeline
# =============================================================================

TeamTrainingPipeline = SequentialAgent(
    name="TeamTrainingPipeline",
    description="Training program creation from HR to content to operations",
    sub_agents=[hr_agent, content_agent, operations_agent],
)


# =============================================================================
# 42. RecruitmentPipeline
# =============================================================================

RecruitmentPipeline = SequentialAgent(
    name="RecruitmentPipeline",
    description="End-to-end hiring workflow with HR and data involvement",
    sub_agents=[hr_agent, data_agent],
)


# =============================================================================
# 43. OnboardingPipeline
# =============================================================================

OnboardingPipeline = SequentialAgent(
    name="OnboardingPipeline",
    description="New employee onboarding through HR, content, and operations",
    sub_agents=[hr_agent, content_agent, operations_agent],
)


# =============================================================================
# 44. PerformanceReviewPipeline
# =============================================================================

PerformanceReviewPipeline = SequentialAgent(
    name="PerformanceReviewPipeline",
    description="Employee performance analysis with HR and data review",
    sub_agents=[hr_agent, data_agent],
)


# =============================================================================
# Exports
# =============================================================================

HR_WORKFLOWS = [
    TeamTrainingPipeline,
    RecruitmentPipeline,
    OnboardingPipeline,
    PerformanceReviewPipeline,
]

__all__ = [
    "TeamTrainingPipeline",
    "RecruitmentPipeline",
    "OnboardingPipeline",
    "PerformanceReviewPipeline",
    "HR_WORKFLOWS",
]
