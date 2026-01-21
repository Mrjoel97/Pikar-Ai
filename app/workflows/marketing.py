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

"""Marketing & Content Workflows (Category 4).

This module implements 8 workflow agents for marketing operations:
19. ContentCampaignPipeline - End-to-end content campaign
20. EmailSequencePipeline - Automated email drip campaigns
21. SocialMediaPipeline - Social content creation & scheduling
22. NewsletterPipeline - Weekly/monthly newsletter creation
23. BlogContentPipeline - SEO-optimized blog creation
24. BrandVoicePipeline - Establish and refine brand voice
25. CampaignAnalyticsPipeline - Campaign performance analysis
26. ABTestingPipeline - Iterative A/B optimization

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, LoopAgent

from app.agents.specialized_agents import (
    strategic_agent,
    content_agent,
    data_agent,
    marketing_agent,
)


# =============================================================================
# 19. ContentCampaignPipeline
# =============================================================================

ContentCampaignPipeline = SequentialAgent(
    name="ContentCampaignPipeline",
    description="End-to-end content campaign from strategy to execution",
    sub_agents=[strategic_agent, content_agent, marketing_agent],
)


# =============================================================================
# 20. EmailSequencePipeline
# =============================================================================

EmailSequencePipeline = SequentialAgent(
    name="EmailSequencePipeline",
    description="Automated email drip campaign creation and analysis",
    sub_agents=[marketing_agent, content_agent, data_agent],
)


# =============================================================================
# 21. SocialMediaPipeline
# =============================================================================

SocialMediaPipeline = SequentialAgent(
    name="SocialMediaPipeline",
    description="Social content creation and scheduling with analytics",
    sub_agents=[content_agent, marketing_agent, data_agent],
)


# =============================================================================
# 22. NewsletterPipeline
# =============================================================================

NewsletterPipeline = SequentialAgent(
    name="NewsletterPipeline",
    description="Weekly/monthly newsletter creation",
    sub_agents=[content_agent, marketing_agent],
)


# =============================================================================
# 23. BlogContentPipeline
# =============================================================================

BlogContentPipeline = SequentialAgent(
    name="BlogContentPipeline",
    description="SEO-optimized blog content creation",
    sub_agents=[strategic_agent, content_agent, data_agent],
)


# =============================================================================
# 24. BrandVoicePipeline
# =============================================================================

BrandVoicePipeline = SequentialAgent(
    name="BrandVoicePipeline",
    description="Establish and refine brand voice guidelines",
    sub_agents=[content_agent, marketing_agent, strategic_agent],
)


# =============================================================================
# 25. CampaignAnalyticsPipeline
# =============================================================================

CampaignAnalyticsPipeline = SequentialAgent(
    name="CampaignAnalyticsPipeline",
    description="Campaign performance analysis and reporting",
    sub_agents=[data_agent, marketing_agent],
)


# =============================================================================
# 26. ABTestingPipeline
# =============================================================================

_ab_test_cycle = SequentialAgent(
    name="ABTestCycle",
    description="Single A/B test iteration with analysis",
    sub_agents=[marketing_agent, data_agent, content_agent],
)

ABTestingPipeline = LoopAgent(
    name="ABTestingPipeline",
    description="Iterative A/B testing optimization until winner found",
    sub_agents=[_ab_test_cycle],
    max_iterations=5,
)


# =============================================================================
# Exports
# =============================================================================

MARKETING_WORKFLOWS = [
    ContentCampaignPipeline,
    EmailSequencePipeline,
    SocialMediaPipeline,
    NewsletterPipeline,
    BlogContentPipeline,
    BrandVoicePipeline,
    CampaignAnalyticsPipeline,
    ABTestingPipeline,
]

__all__ = [
    "ContentCampaignPipeline",
    "EmailSequencePipeline",
    "SocialMediaPipeline",
    "NewsletterPipeline",
    "BlogContentPipeline",
    "BrandVoicePipeline",
    "CampaignAnalyticsPipeline",
    "ABTestingPipeline",
    "MARKETING_WORKFLOWS",
]
