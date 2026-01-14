"""
SRE Automation Module for Toil Reduction

This module implements Google SRE principles for reducing toil:
- Manual task identification and tracking
- Auto-remediation and self-healing systems
- Runbook automation
- SLO-based alerting
- Error budget tracking
"""

from .toil_tracker import ToilTracker, ToilMetrics
from .runbook_automation import RunbookEngine, RunbookExecutor
from .slo_manager import SLOManager, ErrorBudget, Alert
from .self_healing import SelfHealingSystem, RemediationAction
from .ticketing_integration import TicketingClient, JiraClient, ServiceNowClient

__all__ = [
    'ToilTracker',
    'ToilMetrics',
    'RunbookEngine',
    'RunbookExecutor',
    'SLOManager',
    'ErrorBudget',
    'Alert',
    'SelfHealingSystem',
    'RemediationAction',
    'TicketingClient',
    'JiraClient',
    'ServiceNowClient'
]

__version__ = '1.0.0'
