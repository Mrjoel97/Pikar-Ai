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

"""Evaluation & Analysis Workflows (Category 6).

This module implements 6 workflow agents for business analysis:
31. BusinessEvaluationPipeline - 360° business health assessment
32. ProjectEvaluationPipeline - Post-project analysis
33. UserActivityAnalysisPipeline - User behavior insights
34. GrowthEvaluationPipeline - Growth trajectory analysis
35. CompetitorAnalysisPipeline - Competitive intelligence
36. MarketResearchPipeline - Comprehensive market analysis

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, ParallelAgent

from app.agents.specialized_agents import (
    strategic_agent,
    content_agent,
    data_agent,
    financial_agent,
    operations_agent,
    marketing_agent,
    sales_agent,
)


# =============================================================================
# 31. BusinessEvaluationPipeline (Consensus Pattern)
# =============================================================================

_business_eval_parallel = ParallelAgent(
    name="BusinessEvalConsensus",
    description="Parallel 360° analysis from financial, data, and strategic perspectives",
    sub_agents=[financial_agent, data_agent, strategic_agent],
)

BusinessEvaluationPipeline = SequentialAgent(
    name="BusinessEvaluationPipeline",
    description="360° business health assessment with multi-perspective consensus",
    sub_agents=[_business_eval_parallel],
)


# =============================================================================
# 32. ProjectEvaluationPipeline
# =============================================================================

ProjectEvaluationPipeline = SequentialAgent(
    name="ProjectEvaluationPipeline",
    description="Post-project analysis through data, operations, and financial review",
    sub_agents=[data_agent, operations_agent, financial_agent],
)


# =============================================================================
# 33. UserActivityAnalysisPipeline
# =============================================================================

UserActivityAnalysisPipeline = SequentialAgent(
    name="UserActivityAnalysisPipeline",
    description="User behavior insights from data to marketing to sales",
    sub_agents=[data_agent, marketing_agent, sales_agent],
)


# =============================================================================
# 34. GrowthEvaluationPipeline
# =============================================================================

GrowthEvaluationPipeline = SequentialAgent(
    name="GrowthEvaluationPipeline",
    description="Growth trajectory analysis through data, financial, and strategic lens",
    sub_agents=[data_agent, financial_agent, strategic_agent],
)


# =============================================================================
# 35. CompetitorAnalysisPipeline
# =============================================================================

CompetitorAnalysisPipeline = SequentialAgent(
    name="CompetitorAnalysisPipeline",
    description="Competitive intelligence gathering and analysis",
    sub_agents=[strategic_agent, data_agent, sales_agent],
)


# =============================================================================
# 36. MarketResearchPipeline
# =============================================================================

_market_research_parallel = ParallelAgent(
    name="MarketResearchGathering",
    description="Parallel market data gathering from data and strategic perspectives",
    sub_agents=[data_agent, strategic_agent],
)

MarketResearchPipeline = SequentialAgent(
    name="MarketResearchPipeline",
    description="Comprehensive market analysis with parallel research and content synthesis",
    sub_agents=[_market_research_parallel, marketing_agent, content_agent],
)


# =============================================================================
# Exports
# =============================================================================

EVALUATION_WORKFLOWS = [
    BusinessEvaluationPipeline,
    ProjectEvaluationPipeline,
    UserActivityAnalysisPipeline,
    GrowthEvaluationPipeline,
    CompetitorAnalysisPipeline,
    MarketResearchPipeline,
]

__all__ = [
    "BusinessEvaluationPipeline",
    "ProjectEvaluationPipeline",
    "UserActivityAnalysisPipeline",
    "GrowthEvaluationPipeline",
    "CompetitorAnalysisPipeline",
    "MarketResearchPipeline",
    "EVALUATION_WORKFLOWS",
]
