"""
Runbook Automation Engine - Self-Healing Systems

Automatically executes runbooks in response to alerts to remediate
common issues without human intervention.
"""

import subprocess
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import yaml
import re

logger = logging.getLogger(__name__)


@dataclass
class RunbookStep:
    """Single step in a runbook"""
    name: str
    action_type: str  # 'command', 'script', 'api_call', 'wait'
    action: str
    timeout: int = 300  # seconds
    retry_count: int = 3
    success_criteria: Optional[str] = None
    rollback_action: Optional[str] = None


@dataclass
class RunbookResult:
    """Result of runbook execution"""
    runbook_name: str
    success: bool
    steps_executed: int
    steps_failed: int
    execution_time: float
    output: List[Dict[str, Any]]
    error_message: Optional[str] = None


class RunbookEngine:
    """
    Engine for defining and managing runbooks
    """

    def __init__(self, runbooks_dir: str = "data/runbooks"):
        self.runbooks_dir = Path(runbooks_dir)
        self.runbooks_dir.mkdir(parents=True, exist_ok=True)
        self.runbooks: Dict[str, List[RunbookStep]] = {}
        self._load_runbooks()

    def _load_runbooks(self):
        """Load runbooks from YAML files"""
        for runbook_file in self.runbooks_dir.glob("*.yaml"):
            try:
                with open(runbook_file, 'r') as f:
                    data = yaml.safe_load(f)
                    runbook_name = data.get('name', runbook_file.stem)
                    steps = [
                        RunbookStep(
                            name=step['name'],
                            action_type=step['action_type'],
                            action=step['action'],
                            timeout=step.get('timeout', 300),
                            retry_count=step.get('retry_count', 3),
                            success_criteria=step.get('success_criteria'),
                            rollback_action=step.get('rollback_action')
                        )
                        for step in data.get('steps', [])
                    ]
                    self.runbooks[runbook_name] = steps
                    logger.info(f"Loaded runbook: {runbook_name} with {len(steps)} steps")
            except Exception as e:
                logger.error(f"Failed to load runbook {runbook_file}: {e}")

    def create_runbook(self,
                       name: str,
                       steps: List[RunbookStep],
                       description: str = "",
                       triggers: List[str] = None) -> bool:
        """
        Create a new runbook

        Args:
            name: Runbook name
            steps: List of RunbookStep objects
            description: Description of what this runbook does
            triggers: List of alert patterns that trigger this runbook

        Returns:
            True if created successfully
        """
        try:
            runbook_data = {
                'name': name,
                'description': description,
                'triggers': triggers or [],
                'steps': [
                    {
                        'name': step.name,
                        'action_type': step.action_type,
                        'action': step.action,
                        'timeout': step.timeout,
                        'retry_count': step.retry_count,
                        'success_criteria': step.success_criteria,
                        'rollback_action': step.rollback_action
                    }
                    for step in steps
                ]
            }

            runbook_path = self.runbooks_dir / f"{name}.yaml"
            with open(runbook_path, 'w') as f:
                yaml.dump(runbook_data, f, default_flow_style=False)

            self.runbooks[name] = steps
            logger.info(f"Created runbook: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create runbook: {e}")
            return False

    def get_runbook(self, name: str) -> Optional[List[RunbookStep]]:
        """Get runbook by name"""
        return self.runbooks.get(name)

    def list_runbooks(self) -> List[str]:
        """List all available runbooks"""
        return list(self.runbooks.keys())


class RunbookExecutor:
    """
    Executes runbooks for auto-remediation
    """

    def __init__(self, engine: RunbookEngine, dry_run: bool = False):
        self.engine = engine
        self.dry_run = dry_run
        self.execution_history: List[RunbookResult] = []

    def execute(self,
                runbook_name: str,
                context: Dict[str, Any] = None) -> RunbookResult:
        """
        Execute a runbook

        Args:
            runbook_name: Name of runbook to execute
            context: Context variables (e.g., alert details, host info)

        Returns:
            RunbookResult with execution details
        """
        start_time = datetime.now()
        context = context or {}

        runbook = self.engine.get_runbook(runbook_name)
        if not runbook:
            logger.error(f"Runbook not found: {runbook_name}")
            return RunbookResult(
                runbook_name=runbook_name,
                success=False,
                steps_executed=0,
                steps_failed=1,
                execution_time=0,
                output=[],
                error_message=f"Runbook not found: {runbook_name}"
            )

        logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Executing runbook: {runbook_name}")

        output = []
        steps_executed = 0
        steps_failed = 0
        rollback_actions = []

        for i, step in enumerate(runbook):
            logger.info(f"Step {i+1}/{len(runbook)}: {step.name}")

            step_result = self._execute_step(step, context)
            output.append(step_result)
            steps_executed += 1

            if step_result['success']:
                # Store rollback action if provided
                if step.rollback_action:
                    rollback_actions.append(step.rollback_action)
            else:
                steps_failed += 1
                logger.error(f"Step failed: {step.name}")

                # Execute rollback if step failed
                if rollback_actions:
                    logger.info("Executing rollback actions...")
                    self._execute_rollback(rollback_actions)

                break

        execution_time = (datetime.now() - start_time).total_seconds()

        result = RunbookResult(
            runbook_name=runbook_name,
            success=(steps_failed == 0),
            steps_executed=steps_executed,
            steps_failed=steps_failed,
            execution_time=execution_time,
            output=output,
            error_message=output[-1]['error'] if steps_failed > 0 else None
        )

        self.execution_history.append(result)
        logger.info(f"Runbook execution completed: {runbook_name} - Success: {result.success}")

        return result

    def _execute_step(self, step: RunbookStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single runbook step"""
        step_result = {
            'step_name': step.name,
            'action_type': step.action_type,
            'success': False,
            'output': '',
            'error': None
        }

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {step.action}")
            step_result['success'] = True
            step_result['output'] = "[DRY RUN] Simulated execution"
            return step_result

        try:
            # Substitute context variables in action
            action = self._substitute_variables(step.action, context)

            if step.action_type == 'command':
                result = self._execute_command(action, step.timeout, step.retry_count)
                step_result['output'] = result['output']
                step_result['success'] = result['success']
                step_result['error'] = result.get('error')

            elif step.action_type == 'script':
                result = self._execute_script(action, step.timeout)
                step_result['output'] = result['output']
                step_result['success'] = result['success']
                step_result['error'] = result.get('error')

            elif step.action_type == 'wait':
                import time
                wait_seconds = int(action)
                time.sleep(wait_seconds)
                step_result['success'] = True
                step_result['output'] = f"Waited {wait_seconds} seconds"

            elif step.action_type == 'api_call':
                # Parse API call format: METHOD URL [body]
                result = self._execute_api_call(action)
                step_result['output'] = result['output']
                step_result['success'] = result['success']
                step_result['error'] = result.get('error')

            # Check success criteria if provided
            if step.success_criteria and step_result['success']:
                if not self._check_success_criteria(
                    step_result['output'],
                    step.success_criteria
                ):
                    step_result['success'] = False
                    step_result['error'] = "Success criteria not met"

        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            step_result['error'] = str(e)

        return step_result

    def _substitute_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Substitute {{variable}} with values from context"""
        for key, value in context.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    def _execute_command(self, command: str, timeout: int, retry_count: int) -> Dict[str, Any]:
        """Execute a shell command with retries"""
        for attempt in range(retry_count):
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                return {
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'error': result.stderr if result.returncode != 0 else None
                }

            except subprocess.TimeoutExpired:
                if attempt < retry_count - 1:
                    logger.warning(f"Command timed out, retrying... (attempt {attempt + 1}/{retry_count})")
                    continue
                return {
                    'success': False,
                    'output': '',
                    'error': f'Command timed out after {timeout} seconds'
                }

            except Exception as e:
                if attempt < retry_count - 1:
                    logger.warning(f"Command failed, retrying... (attempt {attempt + 1}/{retry_count})")
                    continue
                return {
                    'success': False,
                    'output': '',
                    'error': str(e)
                }

    def _execute_script(self, script_path: str, timeout: int) -> Dict[str, Any]:
        """Execute a script file"""
        script_file = Path(script_path)
        if not script_file.exists():
            return {
                'success': False,
                'output': '',
                'error': f'Script not found: {script_path}'
            }

        return self._execute_command(f"bash {script_path}", timeout, 1)

    def _execute_api_call(self, api_spec: str) -> Dict[str, Any]:
        """Execute an API call"""
        try:
            import requests

            # Parse: METHOD URL [JSON_BODY]
            parts = api_spec.split(maxsplit=2)
            method = parts[0].upper()
            url = parts[1]
            body = json.loads(parts[2]) if len(parts) > 2 else None

            response = requests.request(
                method=method,
                url=url,
                json=body,
                timeout=30
            )

            return {
                'success': response.status_code < 400,
                'output': response.text,
                'error': f'HTTP {response.status_code}' if response.status_code >= 400 else None
            }

        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }

    def _check_success_criteria(self, output: str, criteria: str) -> bool:
        """Check if output meets success criteria (regex pattern)"""
        try:
            return bool(re.search(criteria, output))
        except Exception as e:
            logger.error(f"Failed to check success criteria: {e}")
            return False

    def _execute_rollback(self, rollback_actions: List[str]):
        """Execute rollback actions in reverse order"""
        for action in reversed(rollback_actions):
            try:
                logger.info(f"Rollback: {action}")
                subprocess.run(action, shell=True, capture_output=True, timeout=60)
            except Exception as e:
                logger.error(f"Rollback action failed: {e}")

    def get_execution_history(self, limit: int = 10) -> List[RunbookResult]:
        """Get recent execution history"""
        return self.execution_history[-limit:]


# Predefined runbooks for common scenarios
COMMON_RUNBOOKS = {
    'disk_cleanup': [
        RunbookStep(
            name="Check disk usage",
            action_type="command",
            action="df -h {{mount_point}}",
            success_criteria=r"\d+%"
        ),
        RunbookStep(
            name="Clean Docker images",
            action_type="command",
            action="docker system prune -af --volumes",
            rollback_action="echo 'No rollback needed'"
        ),
        RunbookStep(
            name="Clean old logs",
            action_type="command",
            action="find /var/log -name '*.log' -mtime +30 -delete",
            rollback_action="echo 'Logs deleted, no rollback'"
        ),
        RunbookStep(
            name="Verify disk space recovered",
            action_type="command",
            action="df -h {{mount_point}}",
            success_criteria=r"[1-7]\d%"  # Less than 80%
        )
    ],

    'container_restart': [
        RunbookStep(
            name="Check container status",
            action_type="command",
            action="docker ps -a --filter name={{container_name}}",
            success_criteria=r"{{container_name}}"
        ),
        RunbookStep(
            name="Get container logs",
            action_type="command",
            action="docker logs --tail 100 {{container_name}}"
        ),
        RunbookStep(
            name="Restart container",
            action_type="command",
            action="docker restart {{container_name}}",
            rollback_action="docker start {{container_name}}"
        ),
        RunbookStep(
            name="Wait for container to be healthy",
            action_type="wait",
            action="10"
        ),
        RunbookStep(
            name="Verify container health",
            action_type="command",
            action="docker inspect --format='{{{{.State.Health.Status}}}}' {{container_name}}",
            success_criteria=r"healthy"
        )
    ],

    'high_memory_remediation': [
        RunbookStep(
            name="Identify high memory processes",
            action_type="command",
            action="ps aux --sort=-%mem | head -10"
        ),
        RunbookStep(
            name="Clear system cache",
            action_type="command",
            action="sync; echo 3 > /proc/sys/vm/drop_caches"
        ),
        RunbookStep(
            name="Restart memory-intensive service",
            action_type="command",
            action="systemctl restart {{service_name}}",
            rollback_action="systemctl start {{service_name}}"
        ),
        RunbookStep(
            name="Verify memory usage",
            action_type="command",
            action="free -h",
            success_criteria=r"available.*[2-9]\d{2,}Mi"  # At least 200MB available
        )
    ],

    'certificate_renewal': [
        RunbookStep(
            name="Check certificate expiry",
            action_type="command",
            action="echo | openssl s_client -servername {{domain}} -connect {{domain}}:443 2>/dev/null | openssl x509 -noout -dates"
        ),
        RunbookStep(
            name="Renew certificate with certbot",
            action_type="command",
            action="certbot renew --cert-name {{domain}} --force-renewal",
            rollback_action="certbot rollback"
        ),
        RunbookStep(
            name="Reload web server",
            action_type="command",
            action="systemctl reload nginx",
            rollback_action="systemctl reload nginx"
        ),
        RunbookStep(
            name="Verify new certificate",
            action_type="command",
            action="echo | openssl s_client -servername {{domain}} -connect {{domain}}:443 2>/dev/null | openssl x509 -noout -dates",
            success_criteria=r"notAfter"
        )
    ]
}


def create_common_runbooks(engine: RunbookEngine):
    """Create predefined runbooks for common scenarios"""
    for name, steps in COMMON_RUNBOOKS.items():
        engine.create_runbook(
            name=name,
            steps=steps,
            description=f"Auto-remediation for {name.replace('_', ' ')}",
            triggers=[name]
        )
    logger.info(f"Created {len(COMMON_RUNBOOKS)} common runbooks")
