"""
Automation Engine

Executes generated workflows and tracks results.
"""

import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading
import queue

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Execute and manage automation workflows"""

    def __init__(self, dry_run: bool = True):
        """
        Initialize automation engine

        Args:
            dry_run: If True, don't actually execute commands
        """
        self.dry_run = dry_run
        self.execution_history = []
        self.active_executions = {}
        self.execution_queue = queue.Queue()

    def execute_workflow(self, workflow: Dict[str, Any],
                        async_execution: bool = False) -> Dict[str, Any]:
        """
        Execute a workflow

        Args:
            workflow: Workflow specification
            async_execution: Execute asynchronously

        Returns:
            Execution result dictionary
        """
        execution_id = f"{workflow['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Executing workflow: {workflow['name']} (ID: {execution_id})")

        if self.dry_run:
            logger.info("DRY RUN MODE - No actual commands will be executed")

        result = {
            'execution_id': execution_id,
            'workflow_name': workflow['name'],
            'started_at': datetime.now().isoformat(),
            'status': 'running',
            'steps_completed': 0,
            'total_steps': len(workflow.get('steps', [])),
            'step_results': [],
            'errors': []
        }

        if async_execution:
            thread = threading.Thread(
                target=self._execute_workflow_steps,
                args=(workflow, result)
            )
            thread.start()
            self.active_executions[execution_id] = {
                'thread': thread,
                'result': result
            }
        else:
            self._execute_workflow_steps(workflow, result)

        return result

    def _execute_workflow_steps(self, workflow: Dict[str, Any],
                                result: Dict[str, Any]) -> None:
        """Execute workflow steps"""
        workflow_type = workflow.get('type', 'bash')

        try:
            for idx, step in enumerate(workflow.get('steps', []), 1):
                logger.info(f"Executing step {idx}/{result['total_steps']}: {step['name']}")

                step_result = self._execute_step(step, workflow_type)
                result['step_results'].append(step_result)

                if step_result['status'] == 'failed':
                    result['status'] = 'failed'
                    result['errors'].append(f"Step {idx} failed: {step_result.get('error', 'Unknown error')}")
                    break

                result['steps_completed'] = idx

            if result['status'] != 'failed':
                result['status'] = 'completed'

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            result['status'] = 'failed'
            result['errors'].append(str(e))

        finally:
            result['completed_at'] = datetime.now().isoformat()
            self.execution_history.append(result)

    def _execute_step(self, step: Dict[str, Any], workflow_type: str) -> Dict[str, Any]:
        """Execute a single workflow step"""
        step_result = {
            'name': step['name'],
            'status': 'success',
            'output': '',
            'error': '',
            'started_at': datetime.now().isoformat()
        }

        try:
            if self.dry_run:
                step_result['output'] = f"[DRY RUN] Would execute: {step.get('command', step.get('code', ''))}"
            else:
                if workflow_type == 'bash':
                    output = self._execute_bash_command(step.get('command', ''))
                    step_result['output'] = output
                elif workflow_type == 'python':
                    output = self._execute_python_code(step.get('code', ''))
                    step_result['output'] = output
                else:
                    step_result['output'] = f"Unsupported workflow type: {workflow_type}"

        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            step_result['status'] = 'failed'
            step_result['error'] = str(e)

        finally:
            step_result['completed_at'] = datetime.now().isoformat()

        return step_result

    def _execute_bash_command(self, command: str, timeout: int = 300) -> str:
        """Execute bash command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Command failed with exit code {result.returncode}: {result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out after {timeout} seconds")

    def _execute_python_code(self, code: str) -> str:
        """Execute Python code"""
        # For safety, we don't actually exec arbitrary code in production
        # This is a placeholder for actual implementation
        logger.warning("Python code execution is disabled for security")
        return f"[SIMULATED] Python code execution: {code[:100]}"

    def execute_script_file(self, script_path: str) -> Dict[str, Any]:
        """
        Execute a workflow script file

        Args:
            script_path: Path to script file

        Returns:
            Execution result
        """
        script_file = Path(script_path)

        if not script_file.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        logger.info(f"Executing script: {script_path}")

        result = {
            'script_path': script_path,
            'started_at': datetime.now().isoformat(),
            'status': 'running'
        }

        try:
            if self.dry_run:
                result['output'] = f"[DRY RUN] Would execute: {script_path}"
                result['status'] = 'completed'
            else:
                # Make script executable
                script_file.chmod(0o755)

                # Execute script
                process_result = subprocess.run(
                    [str(script_file)],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                result['output'] = process_result.stdout
                result['error'] = process_result.stderr
                result['exit_code'] = process_result.returncode
                result['status'] = 'completed' if process_result.returncode == 0 else 'failed'

        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)

        finally:
            result['completed_at'] = datetime.now().isoformat()
            self.execution_history.append(result)

        return result

    def execute_docker_workflow(self, bundle_dir: str) -> Dict[str, Any]:
        """
        Execute workflow in Docker container

        Args:
            bundle_dir: Path to workflow bundle directory

        Returns:
            Execution result
        """
        bundle_path = Path(bundle_dir)

        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle directory not found: {bundle_dir}")

        dockerfile = bundle_path / 'Dockerfile'
        if not dockerfile.exists():
            raise FileNotFoundError(f"Dockerfile not found in bundle")

        logger.info(f"Building Docker image for workflow: {bundle_path.name}")

        result = {
            'bundle_dir': bundle_dir,
            'started_at': datetime.now().isoformat(),
            'status': 'running',
            'build_output': '',
            'run_output': ''
        }

        try:
            if self.dry_run:
                result['build_output'] = f"[DRY RUN] Would build Docker image from {bundle_dir}"
                result['run_output'] = f"[DRY RUN] Would run Docker container"
                result['status'] = 'completed'
            else:
                # Build Docker image
                image_name = f"sponge-workflow-{bundle_path.name}".lower()

                build_result = subprocess.run(
                    ['docker', 'build', '-t', image_name, str(bundle_path)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if build_result.returncode != 0:
                    raise RuntimeError(f"Docker build failed: {build_result.stderr}")

                result['build_output'] = build_result.stdout
                result['image_name'] = image_name

                # Run Docker container
                run_result = subprocess.run(
                    ['docker', 'run', '--rm', image_name],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                result['run_output'] = run_result.stdout
                result['exit_code'] = run_result.returncode
                result['status'] = 'completed' if run_result.returncode == 0 else 'failed'

        except Exception as e:
            logger.error(f"Docker execution failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)

        finally:
            result['completed_at'] = datetime.now().isoformat()
            self.execution_history.append(result)

        return result

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an execution

        Args:
            execution_id: Execution ID

        Returns:
            Execution result or None if not found
        """
        # Check active executions
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]['result']

        # Check history
        for result in self.execution_history:
            if result.get('execution_id') == execution_id:
                return result

        return None

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get execution history

        Args:
            limit: Maximum number of results

        Returns:
            List of execution results
        """
        return self.execution_history[-limit:]

    def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution

        Args:
            execution_id: Execution ID

        Returns:
            True if cancelled successfully
        """
        if execution_id not in self.active_executions:
            logger.warning(f"Execution not found: {execution_id}")
            return False

        # In a real implementation, we would terminate the thread/process
        logger.info(f"Cancelling execution: {execution_id}")

        execution = self.active_executions[execution_id]
        execution['result']['status'] = 'cancelled'
        execution['result']['completed_at'] = datetime.now().isoformat()

        del self.active_executions[execution_id]

        return True

    def save_execution_log(self, execution_id: str, output_file: str) -> bool:
        """
        Save execution log to file

        Args:
            execution_id: Execution ID
            output_file: Output file path

        Returns:
            True if saved successfully
        """
        result = self.get_execution_status(execution_id)

        if result is None:
            logger.error(f"Execution not found: {execution_id}")
            return False

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"Execution log saved to {output_path}")
        return True

    def clear_history(self, older_than_days: int = 30) -> int:
        """
        Clear old execution history

        Args:
            older_than_days: Clear executions older than this many days

        Returns:
            Number of entries cleared
        """
        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 3600)

        initial_count = len(self.execution_history)

        self.execution_history = [
            result for result in self.execution_history
            if datetime.fromisoformat(result['started_at']).timestamp() > cutoff_time
        ]

        cleared = initial_count - len(self.execution_history)
        logger.info(f"Cleared {cleared} old execution records")

        return cleared
