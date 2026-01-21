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

"""Product & Service Creation Workflows (Category 2).

This module implements 5 workflow agents for product lifecycle:
7. ProductIdeationPipeline - Market-informed product concept
8. ProductValidationPipeline - ROI and market viability assessment
9. ServiceDesignPipeline - Service blueprint and pricing
10. ProductLaunchPipeline - Full product launch coordination
11. ProductIterationPipeline - Continuous product improvement

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

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
# 7. ProductIdeationPipeline
# =============================================================================

ProductIdeationPipeline = SequentialAgent(
    name="ProductIdeationPipeline",
    description="Market-informed product concept development through strategic, data, and content analysis",
    sub_agents=[strategic_agent, data_agent, content_agent],
)


# =============================================================================
# 8. ProductValidationPipeline (Consensus Pattern)
# =============================================================================

_product_validation_parallel = ParallelAgent(
    name="ProductValidationConsensus",
    description="Parallel ROI and viability analysis from financial, data, and strategic perspectives",
    sub_agents=[financial_agent, data_agent, strategic_agent],
)

ProductValidationPipeline = SequentialAgent(
    name="ProductValidationPipeline",
    description="ROI and market viability assessment with multi-perspective consensus",
    sub_agents=[_product_validation_parallel],
)


# =============================================================================
# 9. ServiceDesignPipeline
# =============================================================================

ServiceDesignPipeline = SequentialAgent(
    name="ServiceDesignPipeline",
    description="Service blueprint and pricing development",
    sub_agents=[strategic_agent, operations_agent, financial_agent],
)


# =============================================================================
# 10. ProductLaunchPipeline
# =============================================================================

_product_launch_parallel = ParallelAgent(
    name="ProductLaunchPrep",
    description="Concurrent launch preparation across marketing, sales, and content",
    sub_agents=[marketing_agent, sales_agent, content_agent],
)

ProductLaunchPipeline = SequentialAgent(
    name="ProductLaunchPipeline",
    description="Full product launch coordination with strategic planning and parallel execution",
    sub_agents=[strategic_agent, _product_launch_parallel],
)


# =============================================================================
# 11. ProductIterationPipeline
# =============================================================================

_product_iteration_cycle = SequentialAgent(
    name="ProductIterationCycle",
    description="Single iteration of product improvement cycle",
    sub_agents=[data_agent, content_agent, strategic_agent],
)

ProductIterationPipeline = LoopAgent(
    name="ProductIterationPipeline",
    description="Continuous product improvement based on feedback loops",
    sub_agents=[_product_iteration_cycle],
    max_iterations=5,
)


# =============================================================================
# Exports
# =============================================================================

PRODUCT_WORKFLOWS = [
    ProductIdeationPipeline,
    ProductValidationPipeline,
    ServiceDesignPipeline,
    ProductLaunchPipeline,
    ProductIterationPipeline,
]

__all__ = [
    "ProductIdeationPipeline",
    "ProductValidationPipeline",
    "ServiceDesignPipeline",
    "ProductLaunchPipeline",
    "ProductIterationPipeline",
    "PRODUCT_WORKFLOWS",
]
