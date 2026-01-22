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

"""Skills Registry - Central registry for agent capabilities.

This module defines the Skill model and SkillsRegistry class that provides
a centralized way for agents to access domain-specific knowledge and tools.
"""

from typing import Callable, Any
from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A modular capability or knowledge unit that agents can use.
    
    Skills can be:
    - Knowledge-based: Provide context/instructions (e.g., SEO checklist)
    - Function-based: Provide executable logic (e.g., calculation)
    """
    name: str = Field(..., description="Unique identifier for the skill")
    description: str = Field(..., description="What this skill does")
    category: str = Field(..., description="Category: finance, hr, marketing, sales, compliance, content, data, support, operations")
    
    # Knowledge content (for prompt injection)
    knowledge: str | None = Field(default=None, description="Domain knowledge to inject into agent context")
    
    # Optional callable for function-based skills
    implementation: Callable[..., Any] | None = Field(default=None, exclude=True, description="Optional function implementation")
    
    class Config:
        arbitrary_types_allowed = True


class SkillsRegistry:
    """Central registry for managing and accessing skills.
    
    Usage:
        registry = SkillsRegistry()
        registry.register(my_skill)
        skill = registry.get("my_skill_name")
    """
    
    _instance: "SkillsRegistry | None" = None
    
    def __new__(cls) -> "SkillsRegistry":
        """Singleton pattern to ensure one global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if not self._initialized:
            self._skills: dict[str, Skill] = {}
            self._initialized = True
    
    def register(self, skill: Skill) -> None:
        """Register a skill in the registry."""
        self._skills[skill.name] = skill
    
    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def get_by_category(self, category: str) -> list[Skill]:
        """Get all skills in a category."""
        return [s for s in self._skills.values() if s.category == category]
    
    def list_all(self) -> list[Skill]:
        """List all registered skills."""
        return list(self._skills.values())
    
    def list_names(self) -> list[str]:
        """List all skill names."""
        return list(self._skills.keys())
    
    def use_skill(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Use a skill - returns knowledge or executes function.
        
        Args:
            name: The skill name to use.
            **kwargs: Arguments to pass if skill has an implementation.
            
        Returns:
            Dictionary with skill output or knowledge.
        """
        skill = self.get(name)
        if not skill:
            return {"success": False, "error": f"Skill '{name}' not found"}
        
        result = {
            "success": True,
            "skill_name": name,
            "description": skill.description,
        }
        
        # If skill has implementation, execute it
        if skill.implementation:
            try:
                output = skill.implementation(**kwargs)
                result["output"] = output
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
        
        # If skill has knowledge, include it
        if skill.knowledge:
            result["knowledge"] = skill.knowledge
        
        return result


# Global registry instance
skills_registry = SkillsRegistry()


def get_skill_tool(skill_name: str) -> Callable:
    """Create a tool function for a specific skill.
    
    This allows skills to be exposed as ADK tools.
    """
    def skill_tool(**kwargs: Any) -> dict:
        """Execute the skill with provided arguments."""
        return skills_registry.use_skill(skill_name, **kwargs)
    
    skill_tool.__name__ = f"use_{skill_name}"
    skill_tool.__doc__ = f"Use the {skill_name} skill."
    
    return skill_tool
