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

"""Lead Generation & Sales Workflows (Category 3).

This module implements 7 workflow agents for sales lifecycle:
12. LeadGenerationPipeline - Generate and qualify leads
13. LeadScoringPipeline - Score and prioritize leads
14. LeadNurturingPipeline - Automated lead nurture sequence
15. SalesFunnelCreationPipeline - Build complete sales funnel
16. DealQualificationPipeline - Smart deal routing
17. OutreachSequencePipeline - Multi-touch outreach campaign
18. CustomerJourneyPipeline - Full customer lifecycle mapping
"""

from google.adk.agents import SequentialAgent, LoopAgent

from app.agents.specialized_agents import (
    strategic_agent,
    content_agent,
    data_agent,
    financial_agent,
    marketing_agent,
    sales_agent,
    customer_support_agent,
)


# =============================================================================
# 12. LeadGenerationPipeline
# =============================================================================

LeadGenerationPipeline = SequentialAgent(
    name="LeadGenerationPipeline",
    description="Generate and qualify leads through marketing, content, and data analysis",
    sub_agents=[marketing_agent, content_agent, data_agent],
)


# =============================================================================
# 13. LeadScoringPipeline
# =============================================================================

LeadScoringPipeline = SequentialAgent(
    name="LeadScoringPipeline",
    description="Score and prioritize leads based on data, sales, and financial analysis",
    sub_agents=[data_agent, sales_agent, financial_agent],
)


# =============================================================================
# 14. LeadNurturingPipeline
# =============================================================================

_nurture_cycle = SequentialAgent(
    name="NurtureCycle",
    description="Single iteration of lead nurture sequence",
    sub_agents=[content_agent, sales_agent, data_agent],
)

LeadNurturingPipeline = LoopAgent(
    name="LeadNurturingPipeline",
    description="Automated lead nurture sequence that loops until conversion",
    sub_agents=[_nurture_cycle],
    max_iterations=10,
)


# =============================================================================
# 15. SalesFunnelCreationPipeline
# =============================================================================

SalesFunnelCreationPipeline = SequentialAgent(
    name="SalesFunnelCreationPipeline",
    description="Build complete sales funnel from strategy to execution",
    sub_agents=[strategic_agent, marketing_agent, sales_agent, content_agent],
)


# =============================================================================
# 16. DealQualificationPipeline
# =============================================================================

# Note: Conditional routing would require custom BaseAgent or callback
# For now, implemented as sequential with sales-first approach
DealQualificationPipeline = SequentialAgent(
    name="DealQualificationPipeline",
    description="Smart deal routing through sales qualification and financial analysis",
    sub_agents=[sales_agent, financial_agent],
)


# =============================================================================
# 17. OutreachSequencePipeline
# =============================================================================

OutreachSequencePipeline = SequentialAgent(
    name="OutreachSequencePipeline",
    description="Multi-touch outreach campaign through sales, content, and marketing",
    sub_agents=[sales_agent, content_agent, marketing_agent],
)


# =============================================================================
# 18. CustomerJourneyPipeline
# =============================================================================

CustomerJourneyPipeline = SequentialAgent(
    name="CustomerJourneyPipeline",
    description="Full customer lifecycle mapping from data to support",
    sub_agents=[data_agent, marketing_agent, sales_agent, customer_support_agent],
)


# =============================================================================
# Exports
# =============================================================================

SALES_WORKFLOWS = [
    LeadGenerationPipeline,
    LeadScoringPipeline,
    LeadNurturingPipeline,
    SalesFunnelCreationPipeline,
    DealQualificationPipeline,
    OutreachSequencePipeline,
    CustomerJourneyPipeline,
]

__all__ = [
    "LeadGenerationPipeline",
    "LeadScoringPipeline",
    "LeadNurturingPipeline",
    "SalesFunnelCreationPipeline",
    "DealQualificationPipeline",
    "OutreachSequencePipeline",
    "CustomerJourneyPipeline",
    "SALES_WORKFLOWS",
]
