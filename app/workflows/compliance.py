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

"""Compliance & Risk Workflows (Category 7).

This module implements 4 workflow agents for compliance management:
37. ComplianceAuditPipeline - Iterative compliance verification
38. RiskAssessmentPipeline - Business risk evaluation
39. PolicyReviewPipeline - Policy update and distribution
40. VendorCompliancePipeline - Third-party compliance check

Note: Executive Agent handles synthesis externally per Agent-Eco-System.md.
"""

from google.adk.agents import SequentialAgent, LoopAgent

from app.agents.specialized_agents import (
    strategic_agent,
    financial_agent,
    operations_agent,
    hr_agent,
    compliance_agent,
)


# =============================================================================
# 37. ComplianceAuditPipeline
# =============================================================================

_compliance_check = SequentialAgent(
    name="ComplianceCheck",
    description="Single iteration of compliance verification",
    sub_agents=[compliance_agent, operations_agent],
)

ComplianceAuditPipeline = LoopAgent(
    name="ComplianceAuditPipeline",
    description="Iterative compliance verification until all criteria pass",
    sub_agents=[_compliance_check],
    max_iterations=5,
)


# =============================================================================
# 38. RiskAssessmentPipeline
# =============================================================================

RiskAssessmentPipeline = SequentialAgent(
    name="RiskAssessmentPipeline",
    description="Business risk evaluation through compliance, financial, and strategic analysis",
    sub_agents=[compliance_agent, financial_agent, strategic_agent],
)


# =============================================================================
# 39. PolicyReviewPipeline
# =============================================================================

PolicyReviewPipeline = SequentialAgent(
    name="PolicyReviewPipeline",
    description="Policy update and distribution through compliance and HR channels",
    sub_agents=[compliance_agent, hr_agent],
)


# =============================================================================
# 40. VendorCompliancePipeline
# =============================================================================

VendorCompliancePipeline = SequentialAgent(
    name="VendorCompliancePipeline",
    description="Third-party vendor compliance verification",
    sub_agents=[compliance_agent, operations_agent, financial_agent],
)


# =============================================================================
# Exports
# =============================================================================

COMPLIANCE_WORKFLOWS = [
    ComplianceAuditPipeline,
    RiskAssessmentPipeline,
    PolicyReviewPipeline,
    VendorCompliancePipeline,
]

__all__ = [
    "ComplianceAuditPipeline",
    "RiskAssessmentPipeline",
    "PolicyReviewPipeline",
    "VendorCompliancePipeline",
    "COMPLIANCE_WORKFLOWS",
]
