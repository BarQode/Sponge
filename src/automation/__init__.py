"""
Automation and Workflow Generation Module

Generates automation scripts and workflows for detected issues.
"""

from .workflow_generator import WorkflowGenerator
from .automation_engine import AutomationEngine
from .script_templates import ScriptTemplates

__all__ = ['WorkflowGenerator', 'AutomationEngine', 'ScriptTemplates']
