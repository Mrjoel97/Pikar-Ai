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

"""Workflow Registry - Central registry for mapping workflow names to factory functions.

This module provides a registry to lookup workflow factory functions by their catalog name,
enabling dynamic workflow dispatch with lazy instantiation.

Updated to use factory functions to avoid ADK's single-parent constraint.
When workflows are requested, factory functions are called to create fresh instances.
"""

from typing import Any, Callable, Optional
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent


class WorkflowRegistry:
    """Central registry for workflow factory function lookup and management.

    Maps workflow catalog names to factory functions that create workflow instances.
    Workflows are instantiated lazily when get() is called, creating fresh agent
    instances to avoid ADK's single-parent constraint.
    """

    _instance: "WorkflowRegistry | None" = None

    def __new__(cls) -> "WorkflowRegistry":
        """Singleton pattern for global access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories = {}
            cls._instance._metadata = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._factories: dict[str, Callable] = {}
            self._metadata: dict[str, dict] = {}
            self._initialized = True
            self._load_default_workflows()
    
    def _load_default_workflows(self) -> None:
        """Load all workflow factory functions from workflow modules."""
        try:
            # Initiative workflows
            from app.workflows.initiative import INITIATIVE_WORKFLOW_FACTORIES
            self.register("Initiative Ideation", INITIATIVE_WORKFLOW_FACTORIES["InitiativeIdeationPipeline"], {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent", "ContentCreationAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Initiative Validation", INITIATIVE_WORKFLOW_FACTORIES["InitiativeValidationPipeline"], {
                "category": "Strategic Planning",
                "agents": ["DataAnalysisAgent", "FinancialAnalysisAgent", "StrategicPlanningAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Initiative Build", INITIATIVE_WORKFLOW_FACTORIES["InitiativeBuildPipeline"], {
                "category": "Strategic Planning",
                "agents": ["OperationsOptimizationAgent", "ContentCreationAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Initiative Test", INITIATIVE_WORKFLOW_FACTORIES["InitiativeTestPipeline"], {
                "category": "Strategic Planning",
                "agents": ["OperationsOptimizationAgent", "DataAnalysisAgent", "ComplianceRiskAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Initiative Launch", INITIATIVE_WORKFLOW_FACTORIES["InitiativeLaunchPipeline"], {
                "category": "Strategic Planning",
                "agents": ["MarketingAutomationAgent", "SalesIntelligenceAgent", "ContentCreationAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Initiative Scale", INITIATIVE_WORKFLOW_FACTORIES["InitiativeScalePipeline"], {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent", "DataAnalysisAgent", "FinancialAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass

        try:
            # Sales workflows
            from app.workflows.sales import SALES_WORKFLOW_FACTORIES
            self.register("Lead Generation", SALES_WORKFLOW_FACTORIES["LeadGenerationPipeline"], {
                "category": "Sales",
                "agents": ["SalesIntelligenceAgent", "DataAnalysisAgent", "MarketingAutomationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Lead Scoring", SALES_WORKFLOW_FACTORIES["LeadScoringPipeline"], {
                "category": "Sales",
                "agents": ["DataAnalysisAgent", "SalesIntelligenceAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Lead Nurturing", SALES_WORKFLOW_FACTORIES["LeadNurturingPipeline"], {
                "category": "Sales",
                "agents": ["MarketingAutomationAgent", "ContentCreationAgent", "SalesIntelligenceAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Sales Funnel Creation", SALES_WORKFLOW_FACTORIES["SalesFunnelCreationPipeline"], {
                "category": "Sales",
                "agents": ["StrategicPlanningAgent", "MarketingAutomationAgent", "SalesIntelligenceAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Deal Qualification", SALES_WORKFLOW_FACTORIES["DealQualificationPipeline"], {
                "category": "Sales",
                "agents": ["SalesIntelligenceAgent", "DataAnalysisAgent", "FinancialAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Outreach Sequence", SALES_WORKFLOW_FACTORIES["OutreachSequencePipeline"], {
                "category": "Sales",
                "agents": ["ContentCreationAgent", "SalesIntelligenceAgent", "MarketingAutomationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Customer Journey Mapping", SALES_WORKFLOW_FACTORIES["CustomerJourneyPipeline"], {
                "category": "Sales",
                "agents": ["StrategicPlanningAgent", "DataAnalysisAgent", "MarketingAutomationAgent", "CustomerSupportAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass

        try:
            # Marketing workflows
            from app.workflows.marketing import MARKETING_WORKFLOW_FACTORIES
            self.register("Content Campaign", MARKETING_WORKFLOW_FACTORIES["ContentCampaignPipeline"], {
                "category": "Marketing",
                "agents": ["StrategicPlanningAgent", "ContentCreationAgent", "MarketingAutomationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Email Sequence", MARKETING_WORKFLOW_FACTORIES["EmailSequencePipeline"], {
                "category": "Marketing",
                "agents": ["MarketingAutomationAgent", "ContentCreationAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Social Media Strategy", MARKETING_WORKFLOW_FACTORIES["SocialMediaPipeline"], {
                "category": "Marketing",
                "agents": ["MarketingAutomationAgent", "ContentCreationAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Newsletter Creation", MARKETING_WORKFLOW_FACTORIES["NewsletterPipeline"], {
                "category": "Marketing",
                "agents": ["ContentCreationAgent", "MarketingAutomationAgent", "DataAnalysisAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Blog Content", MARKETING_WORKFLOW_FACTORIES["BlogContentPipeline"], {
                "category": "Marketing",
                "agents": ["ContentCreationAgent", "DataAnalysisAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Brand Voice Development", MARKETING_WORKFLOW_FACTORIES["BrandVoicePipeline"], {
                "category": "Marketing",
                "agents": ["StrategicPlanningAgent", "ContentCreationAgent", "MarketingAutomationAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Campaign Analytics", MARKETING_WORKFLOW_FACTORIES["CampaignAnalyticsPipeline"], {
                "category": "Marketing",
                "agents": ["DataAnalysisAgent", "MarketingAutomationAgent", "StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("A/B Testing", MARKETING_WORKFLOW_FACTORIES["ABTestingPipeline"], {
                "category": "Marketing",
                "agents": ["DataAnalysisAgent", "MarketingAutomationAgent", "ContentCreationAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Landing Page Creation", MARKETING_WORKFLOW_FACTORIES["LandingPageCreationPipeline"], {
                "category": "Marketing",
                "agents": ["StrategicPlanningAgent", "DataAnalysisAgent", "MarketingAutomationAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Form Creation", MARKETING_WORKFLOW_FACTORIES["FormCreationPipeline"], {
                "category": "Marketing",
                "agents": ["MarketingAutomationAgent", "DataAnalysisAgent"],
                "pattern": "LoopAgent",
            })
        except ImportError:
            pass

        try:
            # HR workflows
            from app.workflows.hr import HR_WORKFLOW_FACTORIES
            self.register("Team Training", HR_WORKFLOW_FACTORIES["TeamTrainingPipeline"], {
                "category": "HR",
                "agents": ["HRRecruitmentAgent", "ContentCreationAgent", "OperationsOptimizationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Recruitment Pipeline", HR_WORKFLOW_FACTORIES["RecruitmentPipeline"], {
                "category": "HR",
                "agents": ["HRRecruitmentAgent", "DataAnalysisAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Employee Onboarding", HR_WORKFLOW_FACTORIES["OnboardingPipeline"], {
                "category": "HR",
                "agents": ["HRRecruitmentAgent", "OperationsOptimizationAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Performance Review", HR_WORKFLOW_FACTORIES["PerformanceReviewPipeline"], {
                "category": "HR",
                "agents": ["HRRecruitmentAgent", "DataAnalysisAgent"],
                "pattern": "LoopAgent",
            })
        except ImportError:
            pass

        try:
            # Compliance workflows
            from app.workflows.compliance import COMPLIANCE_WORKFLOW_FACTORIES
            self.register("Compliance Audit", COMPLIANCE_WORKFLOW_FACTORIES["ComplianceAuditPipeline"], {
                "category": "Compliance",
                "agents": ["ComplianceRiskAgent", "DataAnalysisAgent", "OperationsOptimizationAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Risk Assessment", COMPLIANCE_WORKFLOW_FACTORIES["RiskAssessmentPipeline"], {
                "category": "Compliance",
                "agents": ["ComplianceRiskAgent", "DataAnalysisAgent", "FinancialAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Policy Review", COMPLIANCE_WORKFLOW_FACTORIES["PolicyReviewPipeline"], {
                "category": "Compliance",
                "agents": ["ComplianceRiskAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Vendor Compliance", COMPLIANCE_WORKFLOW_FACTORIES["VendorCompliancePipeline"], {
                "category": "Compliance",
                "agents": ["ComplianceRiskAgent", "DataAnalysisAgent", "OperationsOptimizationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass

        try:
            # Product workflows
            from app.workflows.product import PRODUCT_WORKFLOW_FACTORIES
            self.register("Product Ideation", PRODUCT_WORKFLOW_FACTORIES["ProductIdeationPipeline"], {
                "category": "Product",
                "agents": ["StrategicPlanningAgent", "DataAnalysisAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Product Validation", PRODUCT_WORKFLOW_FACTORIES["ProductValidationPipeline"], {
                "category": "Product",
                "agents": ["DataAnalysisAgent", "FinancialAnalysisAgent", "CustomerSupportAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Service Design", PRODUCT_WORKFLOW_FACTORIES["ServiceDesignPipeline"], {
                "category": "Product",
                "agents": ["StrategicPlanningAgent", "OperationsOptimizationAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Product Launch", PRODUCT_WORKFLOW_FACTORIES["ProductLaunchPipeline"], {
                "category": "Product",
                "agents": ["MarketingAutomationAgent", "SalesIntelligenceAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Product Iteration", PRODUCT_WORKFLOW_FACTORIES["ProductIterationPipeline"], {
                "category": "Product",
                "agents": ["DataAnalysisAgent", "CustomerSupportAgent", "StrategicPlanningAgent"],
                "pattern": "LoopAgent",
            })
        except ImportError:
            pass

        try:
            # Documentation workflows
            from app.workflows.documentation import DOCUMENTATION_WORKFLOW_FACTORIES
            self.register("Business Documentation", DOCUMENTATION_WORKFLOW_FACTORIES["BusinessDocumentationPipeline"], {
                "category": "Operations",
                "agents": ["ContentCreationAgent", "StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Project Documentation", DOCUMENTATION_WORKFLOW_FACTORIES["ProjectDocumentationPipeline"], {
                "category": "Operations",
                "agents": ["ContentCreationAgent", "OperationsOptimizationAgent", "DataAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Report Creation", DOCUMENTATION_WORKFLOW_FACTORIES["ReportCreationPipeline"], {
                "category": "Operations",
                "agents": ["DataAnalysisAgent", "FinancialAnalysisAgent", "ContentCreationAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Board Presentation", DOCUMENTATION_WORKFLOW_FACTORIES["BoardPresentationPipeline"], {
                "category": "Operations",
                "agents": ["StrategicPlanningAgent", "FinancialAnalysisAgent", "ContentCreationAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Weekly Briefing", DOCUMENTATION_WORKFLOW_FACTORIES["WeeklyBriefingPipeline"], {
                "category": "Operations",
                "agents": ["DataAnalysisAgent", "StrategicPlanningAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass

        try:
            # Goals workflows
            from app.workflows.goals import GOALS_WORKFLOW_FACTORIES
            self.register("OKR Creation", GOALS_WORKFLOW_FACTORIES["OKRCreationPipeline"], {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent", "DataAnalysisAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Goal Tracking", GOALS_WORKFLOW_FACTORIES["GoalTrackingPipeline"], {
                "category": "Strategic Planning",
                "agents": ["DataAnalysisAgent", "StrategicPlanningAgent"],
                "pattern": "LoopAgent",
            })
            self.register("KPI Dashboard", GOALS_WORKFLOW_FACTORIES["KPIDashboardPipeline"], {
                "category": "Strategic Planning",
                "agents": ["DataAnalysisAgent", "FinancialAnalysisAgent", "ContentCreationAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Quarterly Review", GOALS_WORKFLOW_FACTORIES["QuarterlyReviewPipeline"], {
                "category": "Strategic Planning",
                "agents": ["StrategicPlanningAgent", "FinancialAnalysisAgent", "DataAnalysisAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass

        try:
            # Evaluation workflows
            from app.workflows.evaluation import EVALUATION_WORKFLOW_FACTORIES
            self.register("Business Evaluation", EVALUATION_WORKFLOW_FACTORIES["BusinessEvaluationPipeline"], {
                "category": "Evaluation",
                "agents": ["FinancialAnalysisAgent", "StrategicPlanningAgent", "DataAnalysisAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Project Evaluation", EVALUATION_WORKFLOW_FACTORIES["ProjectEvaluationPipeline"], {
                "category": "Evaluation",
                "agents": ["DataAnalysisAgent", "OperationsOptimizationAgent", "StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("User Activity Analysis", EVALUATION_WORKFLOW_FACTORIES["UserActivityAnalysisPipeline"], {
                "category": "Evaluation",
                "agents": ["DataAnalysisAgent", "CustomerSupportAgent", "MarketingAutomationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Growth Evaluation", EVALUATION_WORKFLOW_FACTORIES["GrowthEvaluationPipeline"], {
                "category": "Evaluation",
                "agents": ["DataAnalysisAgent", "FinancialAnalysisAgent", "StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Competitor Analysis", EVALUATION_WORKFLOW_FACTORIES["CompetitorAnalysisPipeline"], {
                "category": "Evaluation",
                "agents": ["DataAnalysisAgent", "MarketingAutomationAgent", "StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Market Research", EVALUATION_WORKFLOW_FACTORIES["MarketResearchPipeline"], {
                "category": "Evaluation",
                "agents": ["DataAnalysisAgent", "SalesIntelligenceAgent", "MarketingAutomationAgent", "StrategicPlanningAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
        except ImportError:
            pass

        try:
            # Knowledge workflows
            from app.workflows.knowledge import KNOWLEDGE_WORKFLOW_FACTORIES
            self.register("Brain Dump Processing", KNOWLEDGE_WORKFLOW_FACTORIES["BrainDumpProcessingPipeline"], {
                "category": "Knowledge",
                "agents": ["ContentCreationAgent", "DataAnalysisAgent", "StrategicPlanningAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Knowledge Extraction", KNOWLEDGE_WORKFLOW_FACTORIES["KnowledgeExtractionPipeline"], {
                "category": "Knowledge",
                "agents": ["DataAnalysisAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Idea Validation", KNOWLEDGE_WORKFLOW_FACTORIES["IdeaValidationPipeline"], {
                "category": "Knowledge",
                "agents": ["DataAnalysisAgent", "FinancialAnalysisAgent", "StrategicPlanningAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Knowledge Base Ingestion", KNOWLEDGE_WORKFLOW_FACTORIES["KnowledgeBaseIngestionPipeline"], {
                "category": "Knowledge",
                "agents": ["ContentCreationAgent", "DataAnalysisAgent"],
                "pattern": "LoopAgent",
            })
        except ImportError:
            pass

        try:
            # Financial workflows
            from app.workflows.financial import FINANCIAL_WORKFLOW_FACTORIES
            self.register("Financial Model Creation", FINANCIAL_WORKFLOW_FACTORIES["FinancialModelCreationPipeline"], {
                "category": "Financial",
                "agents": ["FinancialAnalysisAgent", "DataAnalysisAgent", "StrategicPlanningAgent", "ComplianceRiskAgent", "ContentCreationAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Budget Planning", FINANCIAL_WORKFLOW_FACTORIES["BudgetPlanningPipeline"], {
                "category": "Financial",
                "agents": ["FinancialAnalysisAgent", "OperationsOptimizationAgent", "StrategicPlanningAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Revenue Analysis", FINANCIAL_WORKFLOW_FACTORIES["RevenueAnalysisPipeline"], {
                "category": "Financial",
                "agents": ["DataAnalysisAgent", "SalesIntelligenceAgent", "FinancialAnalysisAgent"],
                "pattern": "SequentialAgent",
            })
            self.register("Cost Optimization", FINANCIAL_WORKFLOW_FACTORIES["CostOptimizationPipeline"], {
                "category": "Financial",
                "agents": ["FinancialAnalysisAgent", "OperationsOptimizationAgent"],
                "pattern": "LoopAgent",
            })
            self.register("Investor Readiness", FINANCIAL_WORKFLOW_FACTORIES["InvestorReadinessPipeline"], {
                "category": "Financial",
                "agents": ["FinancialAnalysisAgent", "StrategicPlanningAgent", "ComplianceRiskAgent", "ContentCreationAgent"],
                "pattern": "ParallelAgent + SequentialAgent",
            })
            self.register("Cash Flow Analysis", FINANCIAL_WORKFLOW_FACTORIES["CashFlowAnalysisPipeline"], {
                "category": "Financial",
                "agents": ["DataAnalysisAgent", "FinancialAnalysisAgent", "OperationsOptimizationAgent"],
                "pattern": "SequentialAgent",
            })
        except ImportError:
            pass

        try:
            # Dynamic workflow generator
            from app.workflows.dynamic import DynamicWorkflowGenerator
            self.register("Dynamic Workflow", lambda: DynamicWorkflowGenerator(), {
                "category": "Meta",
                "agents": ["All Available"],
                "pattern": "Dynamic",
            })
        except ImportError:
            pass

    def register(self, name: str, factory: Callable, metadata: dict = None) -> None:
        """Register a workflow factory function with the registry.

        Args:
            name: Catalog name of the workflow.
            factory: Factory function that creates workflow instances.
            metadata: Optional metadata about the workflow.
        """
        self._factories[name] = factory
        self._metadata[name] = metadata or {}

    def get(self, name: str, create_instance: bool = True) -> Optional[Any]:
        """Get a workflow by its catalog name.

        By default, calls the factory function to create a fresh workflow instance.
        This ensures workflows don't share agent instances that might have parents.

        Args:
            name: The catalog name of the workflow.
            create_instance: If True (default), call factory to create instance.
                           If False, return the factory function itself.

        Returns:
            A new workflow instance, the factory function, or None if not found.
        """
        factory = self._factories.get(name)
        if factory is None:
            return None

        if create_instance:
            return factory()
        return factory

    def get_factory(self, name: str) -> Optional[Callable]:
        """Get the factory function for a workflow.

        Args:
            name: The catalog name of the workflow.

        Returns:
            The factory function or None if not found.
        """
        return self._factories.get(name)
    
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
        return list(self._factories.keys())

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
        total = len(self._factories)
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


def get_workflow(name: str, create_instance: bool = True) -> Any | None:
    """Convenience function to get a workflow by name.

    Calls the factory function to create a fresh workflow instance.

    Args:
        name: Catalog name of the workflow.
        create_instance: If True (default), create a new instance.

    Returns:
        A new workflow instance or None if not found.
    """
    return workflow_registry.get(name, create_instance=create_instance)


def get_workflow_factory(name: str) -> Optional[Callable]:
    """Convenience function to get a workflow factory function.

    Args:
        name: Catalog name of the workflow.

    Returns:
        The factory function or None if not found.
    """
    return workflow_registry.get_factory(name)


def list_workflows() -> list[str]:
    """Convenience function to list all workflows."""
    return workflow_registry.list_all()
