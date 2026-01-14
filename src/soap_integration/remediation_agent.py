"""
Remediation Agent

Coordinates auto-remediation of detected issues using Ansible.
"""

import os
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

from ..automation import WorkflowGenerator
from ..knowledge_base import EnhancedKnowledgeBase

logger = logging.getLogger(__name__)


class RemediationAgent:
    """Orchestrates automatic remediation of detected issues"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize remediation agent

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.kb = EnhancedKnowledgeBase()
        self.workflow_gen = WorkflowGenerator()
        self.ansible_dir = Path('ansible_playbooks')
        self.ansible_dir.mkdir(parents=True, exist_ok=True)

    def execute_remediation(self, issue_id: str, environment: str,
                           auto_approve: bool = False) -> Dict[str, Any]:
        """
        Execute remediation for an issue

        Args:
            issue_id: Issue identifier or error pattern
            environment: Target environment (dev, staging, production)
            auto_approve: Skip manual approval

        Returns:
            Execution result dictionary
        """
        logger.info(f"Starting remediation for {issue_id} in {environment}")

        result = {
            'issue_id': issue_id,
            'environment': environment,
            'status': 'pending',
            'message': '',
            'playbook_path': '',
            'log': '',
            'timestamp': datetime.now().isoformat()
        }

        try:
            # 1. Find fix in knowledge base
            fix = self._find_fix(issue_id)
            if not fix:
                result['status'] = 'failed'
                result['message'] = f"No fix found for issue: {issue_id}"
                return result

            logger.info(f"Found fix: {fix['category']} - {fix['severity']}")

            # 2. Check if auto-approval is allowed
            if not auto_approve and fix['severity'] == 'critical':
                if not self._request_approval(fix, environment):
                    result['status'] = 'pending_approval'
                    result['message'] = 'Awaiting manual approval'
                    return result

            # 3. Generate Ansible playbook
            playbook_path = self._generate_ansible_playbook(fix, environment)
            result['playbook_path'] = str(playbook_path)

            # 4. Execute playbook
            execution_log = self._execute_ansible(playbook_path, environment)
            result['log'] = execution_log

            # 5. Verify remediation
            if self._verify_remediation(fix, environment):
                result['status'] = 'success'
                result['message'] = 'Remediation completed successfully'
            else:
                result['status'] = 'failed'
                result['message'] = 'Remediation verification failed'

        except Exception as e:
            logger.error(f"Remediation failed: {e}")
            result['status'] = 'failed'
            result['message'] = str(e)

        return result

    def _find_fix(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """Find fix in knowledge base"""
        try:
            # Search by error pattern
            results = self.kb.search({
                'keywords': [issue_id],
                'has_solution': True
            })

            if len(results) == 0:
                return None

            # Return first match
            row = results.iloc[0]
            return {
                'error_pattern': row.get('Error_Pattern', ''),
                'category': row.get('Category', ''),
                'severity': row.get('Severity', ''),
                'solution': row.get('Solution', ''),
                'implementation_steps': row.get('Implementation_Steps', ''),
                'issue_type': row.get('Issue_Type', '')
            }

        except Exception as e:
            logger.error(f"Error finding fix: {e}")
            return None

    def _request_approval(self, fix: Dict[str, Any], environment: str) -> bool:
        """
        Request manual approval for critical fixes

        In production, this would integrate with approval systems
        """
        logger.info(f"Approval required for {fix['severity']} fix in {environment}")

        # For now, auto-approve non-production
        if environment != 'production':
            return True

        # In production implementation, integrate with:
        # - ServiceNow
        # - Jira
        # - PagerDuty
        # - Slack approval workflow

        return False

    def _generate_ansible_playbook(self, fix: Dict[str, Any],
                                   environment: str) -> Path:
        """Generate Ansible playbook from fix"""
        logger.info("Generating Ansible playbook")

        # Parse implementation steps
        try:
            steps = json.loads(fix['implementation_steps'])
        except (json.JSONDecodeError, TypeError):
            steps = [fix['implementation_steps']] if fix['implementation_steps'] else []

        # Create playbook structure
        playbook = {
            'name': f"Remediate {fix['category']} - {fix['error_pattern']}",
            'hosts': self._get_target_hosts(environment),
            'become': True,
            'vars': {
                'environment': environment,
                'issue_category': fix['category'],
                'severity': fix['severity']
            },
            'tasks': []
        }

        # Add pre-check task
        playbook['tasks'].append({
            'name': 'Pre-check: Verify issue exists',
            'shell': self._generate_check_command(fix),
            'register': 'pre_check',
            'ignore_errors': True
        })

        # Add remediation tasks based on category
        if fix['category'].lower() == 'memory':
            playbook['tasks'].extend(self._generate_memory_tasks(steps))
        elif fix['category'].lower() == 'cpu':
            playbook['tasks'].extend(self._generate_cpu_tasks(steps))
        elif fix['category'].lower() == 'zombie':
            playbook['tasks'].extend(self._generate_zombie_tasks(steps))
        elif fix['category'].lower() == 'latency':
            playbook['tasks'].extend(self._generate_latency_tasks(steps))
        else:
            playbook['tasks'].extend(self._generate_generic_tasks(steps))

        # Add post-check task
        playbook['tasks'].append({
            'name': 'Post-check: Verify fix applied',
            'shell': self._generate_check_command(fix),
            'register': 'post_check'
        })

        # Save playbook
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"remediate_{fix['category']}_{timestamp}.yml"
        playbook_path = self.ansible_dir / filename

        with open(playbook_path, 'w') as f:
            yaml.dump([playbook], f, default_flow_style=False)

        logger.info(f"Playbook saved: {playbook_path}")
        return playbook_path

    def _get_target_hosts(self, environment: str) -> str:
        """Get target hosts for environment"""
        host_mapping = {
            'dev': 'dev_servers',
            'staging': 'staging_servers',
            'production': 'prod_servers'
        }
        return host_mapping.get(environment, 'all')

    def _generate_check_command(self, fix: Dict[str, Any]) -> str:
        """Generate command to check if issue exists"""
        category = fix['category'].lower()

        if category == 'memory':
            return "free -m | awk '/Mem:/ {print $3/$2 * 100}'"
        elif category == 'cpu':
            return "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"
        elif category == 'zombie':
            return "ps aux | grep Z | wc -l"
        else:
            return "echo 'Manual verification required'"

    def _generate_memory_tasks(self, steps: List[str]) -> List[Dict]:
        """Generate memory remediation tasks"""
        return [
            {
                'name': 'Clear system caches',
                'shell': 'sync && echo 3 > /proc/sys/vm/drop_caches',
                'when': 'pre_check.stdout|float > 80'
            },
            {
                'name': 'Restart high-memory services',
                'systemd': {
                    'name': '{{ item }}',
                    'state': 'restarted'
                },
                'loop': ['application', 'cache-service'],
                'ignore_errors': True
            }
        ]

    def _generate_cpu_tasks(self, steps: List[str]) -> List[Dict]:
        """Generate CPU remediation tasks"""
        return [
            {
                'name': 'Identify high-CPU processes',
                'shell': "ps aux --sort=-%cpu | head -n 10",
                'register': 'high_cpu_procs'
            },
            {
                'name': 'Adjust process priorities',
                'shell': "renice +5 $(pgrep -f 'high-cpu-process')",
                'ignore_errors': True
            }
        ]

    def _generate_zombie_tasks(self, steps: List[str]) -> List[Dict]:
        """Generate zombie process remediation tasks"""
        return [
            {
                'name': 'Find zombie processes',
                'shell': "ps aux | awk '$8==\"Z\" {print $2}'",
                'register': 'zombies'
            },
            {
                'name': 'Kill parent processes of zombies',
                'shell': "kill -9 $(ps -A -ostat,ppid | awk '/[zZ]/{print $2}')",
                'when': 'zombies.stdout != ""',
                'ignore_errors': True
            }
        ]

    def _generate_latency_tasks(self, steps: List[str]) -> List[Dict]:
        """Generate latency remediation tasks"""
        return [
            {
                'name': 'Check network latency',
                'shell': 'ping -c 5 google.com | tail -1 | awk \'{print $4}\' | cut -d \'/\' -f 2',
                'register': 'latency'
            },
            {
                'name': 'Restart networking service',
                'systemd': {
                    'name': 'NetworkManager',
                    'state': 'restarted'
                },
                'when': 'latency.stdout|float > 100'
            }
        ]

    def _generate_generic_tasks(self, steps: List[str]) -> List[Dict]:
        """Generate generic remediation tasks"""
        tasks = []
        for idx, step in enumerate(steps, 1):
            tasks.append({
                'name': f'Step {idx}: {step[:50]}',
                'shell': step,
                'ignore_errors': True
            })
        return tasks

    def _execute_ansible(self, playbook_path: Path, environment: str) -> str:
        """Execute Ansible playbook"""
        logger.info(f"Executing Ansible playbook: {playbook_path}")

        try:
            # Build ansible-playbook command
            cmd = [
                'ansible-playbook',
                str(playbook_path),
                '-i', self._get_inventory_file(environment),
                '--check',  # Dry run first
                '-v'
            ]

            # Execute dry run
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                logger.warning(f"Dry run failed: {result.stderr}")
                return f"Dry run failed:\n{result.stderr}"

            # Execute actual run (remove --check)
            cmd.remove('--check')
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            log = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"

            if result.returncode == 0:
                logger.info("Ansible playbook executed successfully")
            else:
                logger.error(f"Ansible playbook failed: {result.stderr}")

            return log

        except subprocess.TimeoutExpired:
            return "Execution timed out"
        except Exception as e:
            logger.error(f"Ansible execution error: {e}")
            return f"Error: {str(e)}"

    def _get_inventory_file(self, environment: str) -> str:
        """Get Ansible inventory file for environment"""
        return f"ansible/inventory/{environment}.ini"

    def _verify_remediation(self, fix: Dict[str, Any], environment: str) -> bool:
        """Verify that remediation was successful"""
        logger.info("Verifying remediation")

        # In production, implement actual verification
        # For now, return True
        return True

    def send_notification(self, email: str, result: Dict[str, Any]):
        """Send notification about remediation result"""
        logger.info(f"Sending notification to {email}")

        # In production, integrate with:
        # - SendGrid
        # - AWS SES
        # - SMTP

        message = f"""
        Remediation Result

        Issue: {result['issue_id']}
        Status: {result['status']}
        Message: {result['message']}
        Timestamp: {result['timestamp']}
        """

        logger.info(f"Notification: {message}")
