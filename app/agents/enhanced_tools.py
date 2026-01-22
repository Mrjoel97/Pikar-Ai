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

"""Enhanced Agent Tools with Skills Integration.

This module provides skill-enhanced tools that agents can use to access
domain-specific knowledge and capabilities from the Skills Registry.
"""

from typing import Any
from app.skills import skills_registry


# =============================================================================
# Core Skills Access Tool
# =============================================================================

def use_skill(skill_name: str, **kwargs: Any) -> dict:
    """Use a skill from the Skills Registry to get domain knowledge or execute a function.
    
    This is the primary interface for agents to access the skills system.
    Skills provide either:
    - Knowledge: Domain expertise as context/instructions
    - Functions: Executable logic with parameters
    
    Args:
        skill_name: Name of the skill to use (e.g., 'analyze_financial_statement').
        **kwargs: Additional arguments to pass to function-based skills.
        
    Returns:
        Dictionary containing skill output, knowledge, or error message.
    """
    return skills_registry.use_skill(skill_name, **kwargs)


def list_available_skills(category: str = None) -> dict:
    """List all available skills, optionally filtered by category.
    
    Args:
        category: Optional category filter (finance, hr, marketing, sales, 
                  compliance, content, data, support, operations).
                  
    Returns:
        Dictionary with list of available skill names and descriptions.
    """
    if category:
        skills = skills_registry.get_by_category(category)
    else:
        skills = skills_registry.list_all()
    
    return {
        "success": True,
        "count": len(skills),
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "has_implementation": s.implementation is not None,
            }
            for s in skills
        ],
    }


# =============================================================================
# Financial Agent Enhanced Tools
# =============================================================================

def analyze_financial_health() -> dict:
    """Analyze financial health using the analyze_financial_statement skill.
    
    Returns:
        Dictionary containing the financial analysis framework and guidance.
    """
    return skills_registry.use_skill("analyze_financial_statement")


def get_revenue_forecast_guidance() -> dict:
    """Get revenue forecasting methodology and framework.
    
    Returns:
        Dictionary with forecasting frameworks and best practices.
    """
    return skills_registry.use_skill("forecast_revenue_growth")


def calculate_burn_rate_guidance() -> dict:
    """Get burn rate calculation guidance for startups.
    
    Returns:
        Dictionary with burn rate formulas and benchmarks.
    """
    return skills_registry.use_skill("calculate_burn_rate")


# =============================================================================
# Operations Agent Enhanced Tools
# =============================================================================

def analyze_process_bottlenecks() -> dict:
    """Get framework for identifying and resolving process bottlenecks.
    
    Returns:
        Dictionary with bottleneck analysis methodology.
    """
    return skills_registry.use_skill("process_bottleneck_analysis")


def get_sop_template() -> dict:
    """Get Standard Operating Procedure template and guidelines.
    
    Returns:
        Dictionary with SOP structure and writing guidelines.
    """
    return skills_registry.use_skill("sop_generation")


# =============================================================================
# Data Analysis Agent Enhanced Tools  
# =============================================================================

def get_anomaly_detection_guidance() -> dict:
    """Get framework for detecting data anomalies and outliers.
    
    Returns:
        Dictionary with anomaly detection methods and thresholds.
    """
    return skills_registry.use_skill("anomaly_detection")


def get_trend_analysis_framework() -> dict:
    """Get methodology for analyzing data trends.
    
    Returns:
        Dictionary with trend analysis techniques and reporting structure.
    """
    return skills_registry.use_skill("trend_analysis")


# =============================================================================
# Customer Support Agent Enhanced Tools
# =============================================================================

def analyze_ticket_sentiment() -> dict:
    """Get framework for analyzing customer sentiment in support tickets.
    
    Returns:
        Dictionary with sentiment classification and response templates.
    """
    return skills_registry.use_skill("ticket_sentiment_analysis")


def assess_churn_risk() -> dict:
    """Get framework for identifying customers at risk of churning.
    
    Returns:
        Dictionary with churn indicators and intervention playbook.
    """
    return skills_registry.use_skill("churn_risk_indicators")


# =============================================================================
# Sales Agent Enhanced Tools
# =============================================================================

def get_lead_qualification_framework() -> dict:
    """Get lead qualification frameworks (BANT, MEDDIC, CHAMP).
    
    Returns:
        Dictionary with qualification criteria and scoring matrix.
    """
    return skills_registry.use_skill("lead_qualification_framework")


def get_objection_handling_scripts() -> dict:
    """Get objection handling techniques and response scripts.
    
    Returns:
        Dictionary with LAER method and common objection responses.
    """
    return skills_registry.use_skill("objection_handling")


def get_competitive_analysis_framework() -> dict:
    """Get framework for analyzing competitors.
    
    Returns:
        Dictionary with competitive intelligence methodology.
    """
    return skills_registry.use_skill("competitive_analysis")


# =============================================================================
# Marketing Agent Enhanced Tools
# =============================================================================

def generate_campaign_ideas() -> dict:
    """Get campaign ideation framework and theme generators.
    
    Returns:
        Dictionary with campaign strategy and theme formulas.
    """
    return skills_registry.use_skill("campaign_ideation")


def get_seo_checklist() -> dict:
    """Get comprehensive SEO audit and optimization checklist.
    
    Returns:
        Dictionary with on-page, off-page, and technical SEO checklist.
    """
    return skills_registry.use_skill("seo_checklist")


def get_social_media_guide() -> dict:
    """Get platform-specific social media best practices.
    
    Returns:
        Dictionary with posting guidelines per platform.
    """
    return skills_registry.use_skill("social_media_guide")


# =============================================================================
# HR Agent Enhanced Tools
# =============================================================================

def get_resume_screening_framework() -> dict:
    """Get structured approach for screening resumes.
    
    Returns:
        Dictionary with screening checklist and scoring matrix.
    """
    return skills_registry.use_skill("resume_screening")


def generate_interview_questions() -> dict:
    """Get behavioral and technical interview question frameworks.
    
    Returns:
        Dictionary with STAR method questions and scorecard template.
    """
    return skills_registry.use_skill("interview_question_generator")


def get_turnover_analysis_framework() -> dict:
    """Get framework for calculating and analyzing employee turnover.
    
    Returns:
        Dictionary with turnover metrics and benchmarks.
    """
    return skills_registry.use_skill("employee_turnover_analysis")


# =============================================================================
# Compliance Agent Enhanced Tools
# =============================================================================

def get_gdpr_audit_checklist() -> dict:
    """Get comprehensive GDPR compliance audit checklist.
    
    Returns:
        Dictionary with GDPR requirements and verification items.
    """
    return skills_registry.use_skill("gdpr_audit_checklist")


def get_risk_assessment_matrix() -> dict:
    """Get framework for assessing and prioritizing organizational risks.
    
    Returns:
        Dictionary with risk scoring and mitigation strategies.
    """
    return skills_registry.use_skill("risk_assessment_matrix")


# =============================================================================
# Content Creation Agent Enhanced Tools
# =============================================================================

def get_blog_writing_framework() -> dict:
    """Get blog writing structure and best practices.
    
    Returns:
        Dictionary with blog structure and SEO integration.
    """
    return skills_registry.use_skill("blog_writing")


def get_social_content_templates() -> dict:
    """Get templates for creating engaging social media content.
    
    Returns:
        Dictionary with hook formulas and content formats.
    """
    return skills_registry.use_skill("social_content")


def generate_image(prompt: str, size: str = "1024x1024") -> dict:
    """Generate an image from a text prompt.
    
    Note: This is a stub implementation. Configure API keys for real generation.
    
    Args:
        prompt: Text description of the image to generate.
        size: Image dimensions (default: 1024x1024).
        
    Returns:
        Dictionary with generated image info (or stub response).
    """
    result = skills_registry.use_skill("image_generation", prompt=prompt, size=size)
    if result.get("success") and result.get("output"):
        return result["output"]
    return result


def generate_short_video(prompt: str, duration: int = 15) -> dict:
    """Generate a short video from a text prompt.
    
    Note: This is a stub implementation. Configure API keys for real generation.
    
    Args:
        prompt: Text description of the video to generate.
        duration: Video duration in seconds (default: 15).
        
    Returns:
        Dictionary with generated video info (or stub response).
    """
    result = skills_registry.use_skill("video_generation", prompt=prompt, duration=duration)
    if result.get("success") and result.get("output"):
        return result["output"]
    return result


# =============================================================================
# Export all enhanced tools by category
# =============================================================================

# Core tools - available to all agents
core_tools = [use_skill, list_available_skills]

# Domain-specific tool collections
financial_tools = [analyze_financial_health, get_revenue_forecast_guidance, calculate_burn_rate_guidance]
operations_tools = [analyze_process_bottlenecks, get_sop_template]
data_tools = [get_anomaly_detection_guidance, get_trend_analysis_framework]
support_tools = [analyze_ticket_sentiment, assess_churn_risk]
sales_tools = [get_lead_qualification_framework, get_objection_handling_scripts, get_competitive_analysis_framework]
marketing_tools = [generate_campaign_ideas, get_seo_checklist, get_social_media_guide]
hr_tools = [get_resume_screening_framework, generate_interview_questions, get_turnover_analysis_framework]
compliance_tools = [get_gdpr_audit_checklist, get_risk_assessment_matrix]
content_tools = [get_blog_writing_framework, get_social_content_templates, generate_image, generate_short_video]
