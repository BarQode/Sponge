"""
Self-Healing System - Automated Incident Response

Integrates SLO alerts with runbook execution for automatic remediation
without human intervention.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from .slo_manager import SLOManager, Alert
from .runbook_automation import RunbookEngine, RunbookExecutor, RunbookResult
from .toil_tracker import ToilTracker

logger = logging.getLogger(__name__)


@dataclass
class RemediationAction:
    """Action taken by self-healing system"""
    action_id: str
    alert_id: str
    runbook_name: str
    triggered_at: datetime
    completed_at: Optional[datetime]
    success: bool
    result: Optional[RunbookResult]
    human_intervention_required: bool


class SelfHealingSystem:
    """
    Self-healing system that responds to alerts automatically

    Monitors SLOs and executes runbooks when thresholds are exceeded.
    Tracks all actions for audit and learning.
    """

    def __init__(self,
                 slo_manager: SLOManager,
                 runbook_engine: RunbookEngine,
                 toil_tracker: Optional[ToilTracker] = None,
                 dry_run: bool = False):
        self.slo_manager = slo_manager
        self.runbook_engine = runbook_engine
        self.runbook_executor = RunbookExecutor(runbook_engine, dry_run)
        self.toil_tracker = toil_tracker
        self.dry_run = dry_run

        # Alert to runbook mapping
        self.remediation_map: Dict[str, str] = {}
        self._init_remediation_map()

        # Action history
        self.action_history: List[RemediationAction] = []

    def _init_remediation_map(self):
        """Initialize mapping of alert patterns to runbooks"""
        # Map SLO names or alert patterns to runbook names
        self.remediation_map = {
            'disk_usage_high': 'disk_cleanup',
            'container_unhealthy': 'container_restart',
            'memory_high': 'high_memory_remediation',
            'certificate_expiring': 'certificate_renewal',
            'api_latency_p99': 'container_restart',  # Restart can fix latency
            'api_error_rate': 'container_restart',
            'database_connection_pool': 'restart_database_pool',
        }

    def register_remediation(self, alert_pattern: str, runbook_name: str):
        """
        Register a runbook to handle a specific alert pattern

        Args:
            alert_pattern: Pattern to match in alert (SLO name or keyword)
            runbook_name: Name of runbook to execute
        """
        self.remediation_map[alert_pattern] = runbook_name
        logger.info(f"Registered remediation: {alert_pattern} -> {runbook_name}")

    def monitor_and_heal(self, check_interval: int = 60) -> List[RemediationAction]:
        """
        Monitor all SLOs and execute remediation if needed

        Args:
            check_interval: How often to check (seconds)

        Returns:
            List of remediation actions taken
        """
        actions_taken = []

        # Check all SLOs
        for slo_name in self.slo_manager.slos.keys():
            alert = self.slo_manager.check_and_alert(slo_name)

            if alert and self._should_auto_remediate(alert):
                action = self.auto_remediate(alert)
                if action:
                    actions_taken.append(action)

        return actions_taken

    def _should_auto_remediate(self, alert: Alert) -> bool:
        """
        Determine if an alert should trigger auto-remediation

        Only auto-remediate if:
        1. We have a registered runbook for this alert
        2. Severity is appropriate (not too low, not requiring human for critical decisions)
        3. We're not in cooldown period from recent action
        """
        # Check if we have a runbook for this alert
        runbook = self._find_runbook_for_alert(alert)
        if not runbook:
            logger.info(f"No runbook found for alert: {alert.slo_name}")
            return False

        # Don't auto-remediate 'page' severity - requires human
        if alert.severity == 'page':
            logger.warning(f"Alert requires human intervention: {alert.message}")
            return False

        # Check cooldown - don't remediate same issue within 5 minutes
        for action in self.action_history[-10:]:  # Check last 10 actions
            if action.alert_id.startswith(alert.slo_name):
                time_since = (datetime.now() - action.triggered_at).total_seconds()
                if time_since < 300:  # 5 minutes
                    logger.info(f"In cooldown period for {alert.slo_name}")
                    return False

        return True

    def _find_runbook_for_alert(self, alert: Alert) -> Optional[str]:
        """Find appropriate runbook for an alert"""
        # Try exact match first
        if alert.slo_name in self.remediation_map:
            return self.remediation_map[alert.slo_name]

        # Try pattern matching
        for pattern, runbook in self.remediation_map.items():
            if pattern in alert.message.lower() or pattern in alert.slo_name.lower():
                return runbook

        return None

    def auto_remediate(self, alert: Alert) -> Optional[RemediationAction]:
        """
        Automatically remediate an alert

        Args:
            alert: Alert to remediate

        Returns:
            RemediationAction describing what was done
        """
        runbook_name = self._find_runbook_for_alert(alert)
        if not runbook_name:
            logger.warning(f"No runbook available for alert: {alert.slo_name}")
            return None

        logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Auto-remediating: {alert.message}")
        logger.info(f"Executing runbook: {runbook_name}")

        # Extract context from alert
        context = self._extract_context_from_alert(alert)

        # Execute runbook
        triggered_at = datetime.now()
        result = self.runbook_executor.execute(runbook_name, context)
        completed_at = datetime.now()

        # Track as toil reduction (automated what would be manual)
        if self.toil_tracker and result.success:
            self.toil_tracker.track_task(
                task_id=f"auto_{alert.alert_id}",
                title=f"Auto-remediated: {alert.slo_name}",
                category='auto_remediation',
                time_spent=result.execution_time / 3600,  # Convert to hours
                is_manual=False,
                is_repetitive=True,
                is_automatable=False,  # Already automated
                frequency_per_week=1,
                automation_difficulty='automated',
                business_impact='high'
            )

        action = RemediationAction(
            action_id=f"action_{alert.alert_id}_{int(triggered_at.timestamp())}",
            alert_id=alert.alert_id,
            runbook_name=runbook_name,
            triggered_at=triggered_at,
            completed_at=completed_at,
            success=result.success,
            result=result,
            human_intervention_required=(not result.success)
        )

        self.action_history.append(action)

        # Resolve alert if remediation succeeded
        if result.success:
            self.slo_manager.resolve_alert(alert.alert_id)
            logger.info(f"Successfully remediated alert: {alert.alert_id}")
        else:
            logger.error(f"Remediation failed for alert: {alert.alert_id}")
            logger.error(f"Error: {result.error_message}")

        return action

    def _extract_context_from_alert(self, alert: Alert) -> Dict[str, Any]:
        """Extract context variables from alert for runbook execution"""
        context = {
            'alert_id': alert.alert_id,
            'slo_name': alert.slo_name,
            'severity': alert.severity,
            'timestamp': alert.triggered_at.isoformat()
        }

        # Parse common patterns from alert message
        message = alert.message.lower()

        # Extract service name
        if 'service' in message:
            parts = message.split()
            for i, part in enumerate(parts):
                if part == 'service' and i + 1 < len(parts):
                    context['service_name'] = parts[i + 1].strip('.,')

        # Extract container name
        if 'container' in message:
            parts = message.split()
            for i, part in enumerate(parts):
                if part == 'container' and i + 1 < len(parts):
                    context['container_name'] = parts[i + 1].strip('.,')

        # Extract mount point for disk issues
        if 'disk' in message or 'filesystem' in message:
            context['mount_point'] = '/'  # Default to root

        # Extract domain for certificate issues
        if 'certificate' in message or 'ssl' in message or 'tls' in message:
            # Try to extract domain from message
            import re
            domain_pattern = r'([a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,})'
            match = re.search(domain_pattern, alert.message)
            if match:
                context['domain'] = match.group(1)

        return context

    def get_action_history(self, limit: int = 10) -> List[RemediationAction]:
        """Get recent remediation actions"""
        return self.action_history[-limit:]

    def get_success_rate(self) -> float:
        """Calculate success rate of auto-remediation"""
        if not self.action_history:
            return 0.0

        successful = sum(1 for action in self.action_history if action.success)
        return (successful / len(self.action_history)) * 100

    def export_report(self, output_path: str) -> bool:
        """
        Export self-healing report

        Args:
            output_path: Path to save JSON report

        Returns:
            True if export successful
        """
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'total_actions': len(self.action_history),
                'successful_actions': sum(1 for a in self.action_history if a.success),
                'failed_actions': sum(1 for a in self.action_history if not a.success),
                'success_rate': self.get_success_rate(),
                'actions': [
                    {
                        'action_id': action.action_id,
                        'alert_id': action.alert_id,
                        'runbook_name': action.runbook_name,
                        'triggered_at': action.triggered_at.isoformat(),
                        'completed_at': action.completed_at.isoformat() if action.completed_at else None,
                        'success': action.success,
                        'execution_time': action.result.execution_time if action.result else 0,
                        'human_intervention_required': action.human_intervention_required
                    }
                    for action in self.action_history[-50:]  # Last 50 actions
                ]
            }

            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Exported self-healing report to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return False


class AlertRouter:
    """
    Routes alerts to appropriate handling mechanisms

    Determines whether an alert should:
    - Trigger auto-remediation
    - Send notification to on-call engineer
    - Create ticket for follow-up
    - Escalate to management
    """

    def __init__(self, self_healing: SelfHealingSystem):
        self.self_healing = self_healing

    def route_alert(self, alert: Alert) -> Dict[str, Any]:
        """
        Route an alert to appropriate handlers

        Args:
            alert: Alert to route

        Returns:
            Dictionary with routing decisions and actions taken
        """
        routing = {
            'alert_id': alert.alert_id,
            'severity': alert.severity,
            'actions': []
        }

        # Try auto-remediation first for warning/critical
        if alert.severity in ['warning', 'critical']:
            if self.self_healing._should_auto_remediate(alert):
                action = self.self_healing.auto_remediate(alert)
                if action:
                    routing['actions'].append({
                        'type': 'auto_remediation',
                        'status': 'success' if action.success else 'failed',
                        'action_id': action.action_id
                    })

                    # If remediation succeeded, we're done
                    if action.success:
                        return routing
                    else:
                        # Remediation failed, escalate
                        routing['actions'].append({
                            'type': 'escalate_to_oncall',
                            'reason': 'auto_remediation_failed'
                        })

        # Page on-call for critical/page severity
        if alert.severity in ['page', 'critical']:
            routing['actions'].append({
                'type': 'page_oncall',
                'message': alert.message
            })

        # Create ticket for follow-up on warnings
        if alert.severity == 'warning':
            routing['actions'].append({
                'type': 'create_ticket',
                'priority': 'medium'
            })

        return routing
