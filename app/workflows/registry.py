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

"""Workflow Registry - Central registry for mapping workflow names to implementations.

This module provides a registry to lookup workflow agents by their catalog name,
enabling dynamic workflow dispatch and validation of catalog alignment.
"""

from typing import Any, Type
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent


class WorkflowRegistry:
    """Central registry for workflow agent lookup and management.
    
    Maps workflow catalog names to their actual implementations,
    providing validation and discovery capabilities.
    """
    
    _instance: "WorkflowRegistry | None" = None
    
    def __new__(cls) -> "WorkflowRegistry":
        """Singleton pattern for global access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._workflows = {}
            cls._instance._metadata = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if not self._initialized:
            self._workflows: dict[str, Any] = {}
            self._metadata: dict[str, dict] = {}
            self._initialized = True
            self._load_default_workflows()
    
    def _load_default_workflows(self) -> None:
        """Load all workflow implementations from workflow modules."""
        try:
            # Initiative workflows
            from app.workflows.initiative import (
                CreateInitiativeWorkflow,
                TrackInitiativeProgressWorkflow,
                InitiativeReviewWorkflow,
            )
            self.register("Create Initiative", CreateInitiativeWorkflow, {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Track Initiative Progress", TrackInitiativeProgressWorkflow, {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent", "DataAnalysisAgent"],
                "pattern": "ParallelAgent",
            })
            self.register("Initiative Review", InitiativeReviewWorkflow, {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent"],
                "pattern": "LoopAgent",
            })
        except ImportError:
            pass
        
        try:
            # Sales workflows
            from app.workflows.sales import (
                LeadQualificationWorkflow,
                DealScoringWorkflow,
                SalesProposalWorkflow,
            )
            self.register("Lead Qualification", LeadQualificationWorkflow, {
                "category": "Sales",
                "agents": ["SalesIntelligenceAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Deal Scoring", DealScoringWorkflow, {
                "category": "Sales",
                "agents": ["SalesIntelligenceAgent", "DataAnalysisAgent"],
                "pattern": "ParallelAgent",
            })
            self.register("Sales Proposal Generation", SalesProposalWorkflow, {
                "category": "Sales",
                "agents": ["SalesIntelligenceAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass
        
        try:
            # Marketing workflows
            from app.workflows.marketing import (
                CampaignPlanningWorkflow,
                ContentCalendarWorkflow,
                AudienceSegmentationWorkflow,
                CampaignAnalysisWorkflow,
            )
            self.register("Campaign Planning", CampaignPlanningWorkflow, {
                "category": "Marketing",
                "agents": ["MarketingAutomationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Content Calendar Creation", ContentCalendarWorkflow, {
                "category": "Marketing",
                "agents": ["MarketingAutomationAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Audience Segmentation", AudienceSegmentationWorkflow, {
                "category": "Marketing",
                "agents": ["MarketingAutomationAgent", "DataAnalysisAgent"],
                "pattern": "ParallelAgent",
            })
            self.register("Campaign Analysis", CampaignAnalysisWorkflow, {
                "category": "Marketing",
                "agents": ["MarketingAutomationAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass
        
        try:
            # HR workflows
            from app.workflows.hr import (
                JobPostingWorkflow,
                CandidateScreeningWorkflow,
                InterviewPrepWorkflow,
                OnboardingWorkflow,
            )
            self.register("Job Posting Creation", JobPostingWorkflow, {
                "category": "HR",
                "agents": ["HRRecruitmentAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Candidate Screening", CandidateScreeningWorkflow, {
                "category": "HR",
                "agents": ["HRRecruitmentAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Interview Preparation", InterviewPrepWorkflow, {
                "category": "HR",
                "agents": ["HRRecruitmentAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Employee Onboarding", OnboardingWorkflow, {
                "category": "HR",
                "agents": ["HRRecruitmentAgent", "OperationsOptimizationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass
        
        try:
            # Compliance workflows
            from app.workflows.compliance import (
                ComplianceAuditWorkflow,
                RiskAssessmentWorkflow,
                PolicyReviewWorkflow,
            )
            self.register("Compliance Audit", ComplianceAuditWorkflow, {
                "category": "Compliance",
                "agents": ["ComplianceRiskAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Risk Assessment", RiskAssessmentWorkflow, {
                "category": "Compliance",
                "agents": ["ComplianceRiskAgent", "DataAnalysisAgent"],
                "pattern": "ParallelAgent",
            })
            self.register("Policy Review", PolicyReviewWorkflow, {
                "category": "Compliance",
                "agents": ["ComplianceRiskAgent"],
                "pattern": "LoopAgent",
            })
        except ImportError:
            pass
        
        try:
            # Product workflows
            from app.workflows.product import (
                ProductLaunchWorkflow,
                FeaturePrioritizationWorkflow,
                CustomerFeedbackWorkflow,
            )
            self.register("Product Launch", ProductLaunchWorkflow, {
                "category": "Product",
                "agents": ["StrategicPlanningAgent", "MarketingAutomationAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Feature Prioritization", FeaturePrioritizationWorkflow, {
                "category": "Product",
                "agents": ["StrategicPlanningAgent", "DataAnalysisAgent"],
                "pattern": "ParallelAgent",
            })
            self.register("Customer Feedback Analysis", CustomerFeedbackWorkflow, {
                "category": "Product",
                "agents": ["CustomerSupportAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass
        
        try:
            # Documentation workflows
            from app.workflows.documentation import (
                DocumentationWorkflow,
                KnowledgeBaseUpdateWorkflow,
            )
            self.register("Documentation Generation", DocumentationWorkflow, {
                "category": "Operations",
                "agents": ["ContentCreationAgent", "OperationsOptimizationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Knowledge Base Update", KnowledgeBaseUpdateWorkflow, {
                "category": "Operations",
                "agents": ["ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass
        
        try:
            # Goals and evaluation workflows
            from app.workflows.goals import (
                OKRCreationWorkflow,
                QuarterlyReviewWorkflow,
            )
            from app.workflows.evaluation import (
                PerformanceEvaluationWorkflow,
                TeamAssessmentWorkflow,
            )
            self.register("OKR Creation", OKRCreationWorkflow, {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Quarterly Business Review", QuarterlyReviewWorkflow, {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent", "FinancialAnalysisAgent", "DataAnalysisAgent"],
                "pattern": "ParallelAgent",
            })
            self.register("Performance Evaluation", PerformanceEvaluationWorkflow, {
                "category": "HR",
                "agents": ["HRRecruitmentAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Team Assessment", TeamAssessmentWorkflow, {
                "category": "HR",
                "agents": ["HRRecruitmentAgent"],
                "pattern": "LoopAgent",
            })
        except ImportError:
            pass
        
        try:
            # Knowledge workflows
            from app.workflows.knowledge import (
                KnowledgeDiscoveryWorkflow,
                InsightExtractionWorkflow,
            )
            self.register("Knowledge Discovery", KnowledgeDiscoveryWorkflow, {
                "category": "Data",
                "agents": ["DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Insight Extraction", InsightExtractionWorkflow, {
                "category": "Data",
                "agents": ["DataAnalysisAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass
        
        try:
            # Dynamic workflows
            from app.workflows.dynamic import (
                DynamicWorkflowBuilder,
            )
            self.register("Dynamic Workflow", DynamicWorkflowBuilder, {
                "category": "Meta",
                "agents": ["ExecutiveAgent"],
                "pattern": "Dynamic",
            })
        except ImportError:
            pass
    
    def register(self, name: str, workflow: Any, metadata: dict = None) -> None:
        """Register a workflow with the registry.
        
        Args:
            name: Catalog name of the workflow.
            workflow: The workflow agent class or instance.
            metadata: Optional metadata about the workflow.
        """
        self._workflows[name] = workflow
        self._metadata[name] = metadata or {}
    
    def get(self, name: str) -> Any | None:
        """Get a workflow by its catalog name.
        
        Args:
            name: The catalog name of the workflow.
            
        Returns:
            The workflow agent or None if not found.
        """
        return self._workflows.get(name)
    
    def get_metadata(self, name: str) -> dict:
        """Get metadata for a workflow.
        
        Args:
            name: The catalog name of the workflow.
            
        Returns:
            Dictionary of workflow metadata.
        """
        return self._metadata.get(name, {})
    
    def list_all(self) -> list[str]:
        """List all registered workflow names."""
        return list(self._workflows.keys())
    
    def list_by_category(self, category: str) -> list[str]:
        """List workflow names filtered by category.
        
        Args:
            category: Category to filter by.
            
        Returns:
            List of workflow names in the category.
        """
        return [
            name for name, meta in self._metadata.items()
            if meta.get("category") == category
        ]
    
    def list_by_agent(self, agent_name: str) -> list[str]:
        """List workflow names that use a specific agent.
        
        Args:
            agent_name: Agent name to filter by.
            
        Returns:
            List of workflow names using the agent.
        """
        return [
            name for name, meta in self._metadata.items()
            if agent_name in meta.get("agents", [])
        ]
    
    def get_status_report(self) -> dict:
        """Get a status report of all registered workflows.
        
        Returns:
            Dictionary with workflow counts and details.
        """
        total = len(self._workflows)
        categories = {}
        patterns = {}
        
        for name, meta in self._metadata.items():
            cat = meta.get("category", "Unknown")
            pat = meta.get("pattern", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
            patterns[pat] = patterns.get(pat, 0) + 1
        
        return {
            "total_workflows": total,
            "by_category": categories,
            "by_pattern": patterns,
            "workflow_names": self.list_all(),
        }


# Global registry instance
workflow_registry = WorkflowRegistry()


def get_workflow(name: str) -> Any | None:
    """Convenience function to get a workflow by name.
    
    Args:
        name: Catalog name of the workflow.
        
    Returns:
        The workflow agent or None if not found.
    """
    return workflow_registry.get(name)


def list_workflows() -> list[str]:
    """Convenience function to list all workflows."""
    return workflow_registry.list_all()
