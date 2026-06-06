# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Convert registered skills into guarded automation templates.

Skills remain the source of expertise.  This module adds the automation
envelope around them: trigger metadata, capability visibility, safe defaults,
and approval gates for high-impact access.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.skills.registry import AgentID, Skill, SkillsRegistry, skills_registry
from app.workflows.execution_contracts import VALID_RISK_LEVELS


class AutomationCapability(str, Enum):
    """Capability tiers an automation may request at runtime."""

    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    NETWORK = "network"
    BROWSER = "browser"
    GIT = "git"
    CONNECTORS = "connectors"
    SECRETS = "secrets"
    DEPLOY = "deploy"
    EXTERNAL_POSTING = "external_posting"
    SPEND = "spend"
    HR_SENSITIVE = "hr_sensitive"


FULL_CAPABILITY_SET: tuple[AutomationCapability, ...] = (
    AutomationCapability.READ_ONLY,
    AutomationCapability.WORKSPACE_WRITE,
    AutomationCapability.NETWORK,
    AutomationCapability.BROWSER,
    AutomationCapability.GIT,
    AutomationCapability.CONNECTORS,
    AutomationCapability.SECRETS,
    AutomationCapability.DEPLOY,
    AutomationCapability.EXTERNAL_POSTING,
    AutomationCapability.SPEND,
    AutomationCapability.HR_SENSITIVE,
)

APPROVAL_GATED_CAPABILITIES: dict[AutomationCapability, tuple[str, str]] = {
    AutomationCapability.GIT: (
        "high",
        "Git operations can alter source history or publish local work.",
    ),
    AutomationCapability.CONNECTORS: (
        "customer_outbound",
        "Connector access can touch third-party systems or user accounts.",
    ),
    AutomationCapability.SECRETS: (
        "high",
        "Secret access can expose credentials or privileged configuration.",
    ),
    AutomationCapability.DEPLOY: (
        "publish",
        "Deployments can publish changes to live environments.",
    ),
    AutomationCapability.EXTERNAL_POSTING: (
        "customer_outbound",
        "External posts, messages, and emails can reach customers or public channels.",
    ),
    AutomationCapability.SPEND: (
        "spend",
        "Spend actions can create financial obligations.",
    ),
    AutomationCapability.HR_SENSITIVE: (
        "hr_sensitive",
        "HR-sensitive actions can affect candidates, employees, or private people data.",
    ),
}

SAFE_DEFAULT_CAPABILITIES = {
    AutomationCapability.READ_ONLY,
    AutomationCapability.WORKSPACE_WRITE,
    AutomationCapability.NETWORK,
    AutomationCapability.BROWSER,
}

AccessMode = Literal["guarded_full", "scoped"]
TriggerType = Literal["manual", "schedule", "event"]


class AutomationApprovalGate(BaseModel):
    """A capability that must pause for approval before execution."""

    capability: AutomationCapability
    risk_level: str
    reason: str
    applies_when: str = "requested_at_runtime"


class AutomationAccessDecision(BaseModel):
    """Result of checking a runtime access request against a template."""

    requested_access: list[AutomationCapability]
    allowed_access: list[AutomationCapability]
    blocked_access: list[str] = Field(default_factory=list)
    approval_required: bool
    approval_gates: list[AutomationApprovalGate] = Field(default_factory=list)


class SkillAutomationTemplate(BaseModel):
    """Automation-ready view of a registered skill."""

    automation_key: str
    skill_name: str
    skill_version: str
    name: str
    description: str
    category: str
    agent_ids: list[str] = Field(default_factory=list)
    trigger_types: list[TriggerType] = Field(default_factory=list)
    default_trigger_type: TriggerType = "manual"
    recommended_schedule_frequency: str | None = None
    available_access: list[AutomationCapability] = Field(default_factory=list)
    suggested_access: list[AutomationCapability] = Field(default_factory=list)
    default_allowed_access: list[AutomationCapability] = Field(default_factory=list)
    approval_gates: list[AutomationApprovalGate] = Field(default_factory=list)
    risk_level: str = "low"
    output_contract: dict[str, Any] = Field(default_factory=dict)
    workflow_context: dict[str, Any] = Field(default_factory=dict)
    human_gate_policy: str = "approval_required_for_gated_capabilities"

    def to_workflow_trigger_context(self) -> dict[str, Any]:
        """Return JSON-safe context for a workflow trigger row."""
        return {
            "automation_kind": "skill",
            "automation_key": self.automation_key,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "category": self.category,
            "default_allowed_access": [
                capability.value for capability in self.default_allowed_access
            ],
            "approval_required_for": [
                gate.capability.value for gate in self.approval_gates
            ],
            "output_contract": self.output_contract,
            "human_gate_policy": self.human_gate_policy,
        }


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower())
    return normalized.strip("_") or "skill"


def _skill_text(skill: Skill) -> str:
    return " ".join(
        part
        for part in (
            skill.name,
            skill.description,
            skill.category,
            skill.knowledge_summary or "",
            (skill.knowledge or "")[:1200],
        )
        if part
    ).lower()


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def _ordered_unique(
    capabilities: Iterable[AutomationCapability],
) -> list[AutomationCapability]:
    seen: set[AutomationCapability] = set()
    ordered: list[AutomationCapability] = []
    for capability in capabilities:
        if capability in seen:
            continue
        seen.add(capability)
        ordered.append(capability)
    return ordered


def _infer_suggested_access(skill: Skill) -> list[AutomationCapability]:
    """Infer helpful non-authoritative access hints from skill content."""
    text = _skill_text(skill)
    capabilities: list[AutomationCapability] = [AutomationCapability.READ_ONLY]

    if _contains_any(
        text,
        (
            "research",
            "search",
            "scrape",
            "monitor",
            "market",
            "competitor",
            "benchmark",
            "trend",
            "seo",
            "website",
            "web ",
        ),
    ):
        capabilities.append(AutomationCapability.NETWORK)

    if _contains_any(text, ("browser", "website", "landing page", "web page", "crawl")):
        capabilities.append(AutomationCapability.BROWSER)

    if _contains_any(
        text,
        (
            "create",
            "draft",
            "generate",
            "write",
            "report",
            "document",
            "template",
            "checklist",
            "sop",
            "dashboard",
            "analysis",
        ),
    ):
        capabilities.append(AutomationCapability.WORKSPACE_WRITE)

    if _contains_any(
        text,
        (
            "crm",
            "hubspot",
            "calendar",
            "gmail",
            "email",
            "slack",
            "linkedin",
            "twitter",
            "social",
            "shopify",
            "notion",
            "sheets",
            "google analytics",
            "search console",
        ),
    ):
        capabilities.append(AutomationCapability.CONNECTORS)

    if _contains_any(text, ("publish", "post ", "posting", "send email", "outreach")):
        capabilities.append(AutomationCapability.EXTERNAL_POSTING)

    if _contains_any(text, ("deploy", "production", "release", "go live")):
        capabilities.append(AutomationCapability.DEPLOY)

    if _contains_any(text, ("budget", "payment", "invoice", "payroll", "spend")):
        capabilities.append(AutomationCapability.SPEND)

    if skill.category.lower() == "hr" or _contains_any(
        text, ("candidate", "employee", "resume", "compensation", "performance review")
    ):
        capabilities.append(AutomationCapability.HR_SENSITIVE)

    return _ordered_unique(capabilities)


def _default_allowed_access(
    suggested_access: Sequence[AutomationCapability],
) -> list[AutomationCapability]:
    return [
        capability
        for capability in suggested_access
        if capability in SAFE_DEFAULT_CAPABILITIES
        and capability not in APPROVAL_GATED_CAPABILITIES
    ]


def _approval_gates_for(
    capabilities: Sequence[AutomationCapability],
) -> list[AutomationApprovalGate]:
    gates: list[AutomationApprovalGate] = []
    for capability in capabilities:
        gate = APPROVAL_GATED_CAPABILITIES.get(capability)
        if gate is None:
            continue
        risk_level, reason = gate
        if risk_level not in VALID_RISK_LEVELS:
            risk_level = "high"
        gates.append(
            AutomationApprovalGate(
                capability=capability,
                risk_level=risk_level,
                reason=reason,
            )
        )
    return gates


def _infer_risk_level(skill: Skill) -> str:
    text = _skill_text(skill)
    category = skill.category.strip().lower()

    if category in {"compliance", "legal"} or _contains_any(
        text, ("contract", "legal", "gdpr", "ccpa", "hipaa", "sox")
    ):
        return "legal"
    if category == "hr" or _contains_any(
        text, ("candidate", "employee", "resume", "compensation", "performance review")
    ):
        return "hr_sensitive"
    if _contains_any(text, ("payroll",)):
        return "payroll"
    if category == "finance" and _contains_any(
        text, ("payment", "invoice", "spend", "budget")
    ):
        return "spend"
    if category in {"marketing", "sales", "support"} or _contains_any(
        text, ("outreach", "send email", "customer", "lead", "crm")
    ):
        return "customer_outbound"
    if category == "content" and _contains_any(text, ("publish", "post", "social")):
        return "publish"
    if AutomationCapability.WORKSPACE_WRITE in _infer_suggested_access(skill):
        return "medium"
    return "low"


def _recommended_schedule_frequency(skill: Skill) -> str | None:
    category = skill.category.strip().lower()
    if category in {"finance", "compliance"}:
        return "monthly"
    if category in {"marketing", "sales", "support", "operations", "data"}:
        return "weekly"
    if category == "hr":
        return "monthly"
    return None


def _agent_ids(skill: Skill) -> list[str]:
    return [agent_id.value for agent_id in skill.agent_ids]


def build_skill_automation_template(
    skill: Skill,
    *,
    access_mode: AccessMode = "guarded_full",
    default_trigger_type: TriggerType = "manual",
) -> SkillAutomationTemplate:
    """Build an automation template for a single skill.

    ``guarded_full`` exposes every capability tier to the agent catalog while
    requiring approval for high-impact tiers. ``scoped`` only exposes inferred
    capabilities for callers that want a tighter catalog.
    """
    suggested_access = _infer_suggested_access(skill)
    available_access = (
        list(FULL_CAPABILITY_SET)
        if access_mode == "guarded_full"
        else list(suggested_access)
    )
    default_allowed = _default_allowed_access(suggested_access)
    automation_key = f"skill:{_slugify(skill.name)}"

    output_contract = {
        "type": "skill_guidance",
        "required_fields": ["summary", "recommendations", "evidence_or_reasoning"],
        "allow_artifacts": True,
    }
    workflow_context = {
        "automation_kind": "skill",
        "skill_name": skill.name,
        "skill_version": skill.version,
        "category": skill.category,
    }

    return SkillAutomationTemplate(
        automation_key=automation_key,
        skill_name=skill.name,
        skill_version=skill.version,
        name=f"Run {skill.name}",
        description=skill.description,
        category=skill.category,
        agent_ids=_agent_ids(skill),
        trigger_types=["manual", "schedule", "event"],
        default_trigger_type=default_trigger_type,
        recommended_schedule_frequency=_recommended_schedule_frequency(skill),
        available_access=available_access,
        suggested_access=suggested_access,
        default_allowed_access=default_allowed,
        approval_gates=_approval_gates_for(available_access),
        risk_level=_infer_risk_level(skill),
        output_contract=output_contract,
        workflow_context=workflow_context,
    )


def _skills_for_catalog(
    registry: SkillsRegistry,
    *,
    agent_id: AgentID | None,
    category: str | None,
) -> list[Skill]:
    if agent_id is not None:
        skills = registry.get_by_agent_id(agent_id)
    elif category:
        skills = registry.get_by_category(category)
    else:
        skills = registry.list_all()

    if category and agent_id is not None:
        normalized_category = category.strip().lower()
        skills = [
            skill
            for skill in skills
            if skill.category.strip().lower() == normalized_category
        ]
    return sorted(skills, key=lambda skill: (skill.category, skill.name))


def build_skill_automation_catalog(
    *,
    registry: SkillsRegistry | None = None,
    agent_id: AgentID | None = None,
    category: str | None = None,
    access_mode: AccessMode = "guarded_full",
    limit: int | None = None,
) -> list[SkillAutomationTemplate]:
    """Build automation templates for registered skills."""
    source = registry or skills_registry
    skills = _skills_for_catalog(source, agent_id=agent_id, category=category)
    if limit is not None:
        skills = skills[: max(0, limit)]
    return [
        build_skill_automation_template(skill, access_mode=access_mode)
        for skill in skills
    ]


def get_skill_automation_template(
    skill_name: str,
    *,
    registry: SkillsRegistry | None = None,
    access_mode: AccessMode = "guarded_full",
) -> SkillAutomationTemplate | None:
    """Return the automation template for one skill, if registered."""
    source = registry or skills_registry
    skill = source.get(skill_name)
    if skill is None:
        return None
    return build_skill_automation_template(skill, access_mode=access_mode)


def _coerce_requested_capabilities(
    requested_access: Iterable[AutomationCapability | str],
) -> tuple[list[AutomationCapability], list[str]]:
    known: list[AutomationCapability] = []
    unknown: list[str] = []
    for raw in requested_access:
        if isinstance(raw, AutomationCapability):
            known.append(raw)
            continue
        value = str(raw).strip().lower().replace("-", "_")
        try:
            known.append(AutomationCapability(value))
        except ValueError:
            unknown.append(str(raw))
    return _ordered_unique(known), unknown


def validate_automation_access(
    template: SkillAutomationTemplate,
    requested_access: Iterable[AutomationCapability | str],
) -> AutomationAccessDecision:
    """Check whether a runtime access request is allowed or approval-gated."""
    requested, unknown = _coerce_requested_capabilities(requested_access)
    available = set(template.available_access)
    allowed = [capability for capability in requested if capability in available]
    blocked = [
        capability.value for capability in requested if capability not in available
    ] + unknown
    approval_gates = [
        gate for gate in template.approval_gates if gate.capability in set(allowed)
    ]

    return AutomationAccessDecision(
        requested_access=requested,
        allowed_access=allowed,
        blocked_access=blocked,
        approval_required=bool(approval_gates),
        approval_gates=approval_gates,
    )


def agent_can_use_skill(template: SkillAutomationTemplate, agent_id: AgentID) -> bool:
    """Whether an agent is directly allowed to use the underlying skill."""
    return not template.agent_ids or agent_id.value in template.agent_ids
