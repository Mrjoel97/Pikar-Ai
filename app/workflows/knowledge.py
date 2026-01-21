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

"""Knowledge & Brain Dump Workflows (Category 10).

This module implements 4 workflow agents for knowledge management:
50. BrainDumpProcessingPipeline - Process and categorize brain dumps
51. KnowledgeExtractionPipeline - Extract insights from documents
52. IdeaValidationPipeline - Validate user ideas across dimensions
53. KnowledgeBaseIngestionPipeline - Process documents/URLs for knowledge base

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

from app.agents.specialized_agents import (
    strategic_agent,
    content_agent,
    data_agent,
    financial_agent,
    compliance_agent,
)


# =============================================================================
# 50. BrainDumpProcessingPipeline
# =============================================================================

BrainDumpProcessingPipeline = SequentialAgent(
    name="BrainDumpProcessingPipeline",
    description="Process and categorize brain dumps into actionable insights",
    sub_agents=[content_agent, data_agent, strategic_agent],
)


# =============================================================================
# 51. KnowledgeExtractionPipeline
# =============================================================================

KnowledgeExtractionPipeline = SequentialAgent(
    name="KnowledgeExtractionPipeline",
    description="Extract insights from documents with data and content analysis",
    sub_agents=[data_agent, content_agent],
)


# =============================================================================
# 52. IdeaValidationPipeline (Consensus Pattern)
# =============================================================================

_idea_validation_parallel = ParallelAgent(
    name="IdeaValidationConsensus",
    description="Parallel idea validation from strategic, financial, and data perspectives",
    sub_agents=[strategic_agent, financial_agent, data_agent],
)

IdeaValidationPipeline = SequentialAgent(
    name="IdeaValidationPipeline",
    description="Validate user ideas across dimensions with multi-perspective consensus",
    sub_agents=[_idea_validation_parallel],
)


# =============================================================================
# 53. KnowledgeBaseIngestionPipeline
# =============================================================================

_ingestion_process = SequentialAgent(
    name="IngestionProcess",
    description="Single iteration of content extraction and validation",
    sub_agents=[data_agent, content_agent, compliance_agent],
)

KnowledgeBaseIngestionPipeline = LoopAgent(
    name="KnowledgeBaseIngestionPipeline",
    description="Process documents, URLs, Google Drive files for knowledge base with validation loop",
    sub_agents=[_ingestion_process],
    max_iterations=3,
)


# =============================================================================
# Exports
# =============================================================================

KNOWLEDGE_WORKFLOWS = [
    BrainDumpProcessingPipeline,
    KnowledgeExtractionPipeline,
    IdeaValidationPipeline,
    KnowledgeBaseIngestionPipeline,
]

__all__ = [
    "BrainDumpProcessingPipeline",
    "KnowledgeExtractionPipeline",
    "IdeaValidationPipeline",
    "KnowledgeBaseIngestionPipeline",
    "KNOWLEDGE_WORKFLOWS",
]
