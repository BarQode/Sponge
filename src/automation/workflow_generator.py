"""
Workflow Generator

Generates automation workflows from detected issues.
"""

import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from .script_templates import ScriptTemplates

logger = logging.getLogger(__name__)


class WorkflowGenerator:
    """Generate automation workflows for issues"""

    def __init__(self, output_dir: str = 'workflows'):
        """
        Initialize workflow generator

        Args:
            output_dir: Directory to save generated workflows
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates = ScriptTemplates()

    def generate_workflow(self, issue_data: Dict[str, Any],
                         workflow_type: str = 'bash') -> Dict[str, Any]:
        """
        Generate workflow for an issue

        Args:
            issue_data: Issue information dictionary
            workflow_type: Type of workflow (bash, python, ansible, docker)

        Returns:
            Workflow specification dictionary
        """
        logger.info(f"Generating {workflow_type} workflow for {issue_data.get('category', 'unknown')}")

        workflow = {
            'name': f"fix_{issue_data.get('issue_type', 'issue').replace(' ', '_')}",
            'description': issue_data.get('Error_Pattern', 'Auto-generated fix'),
            'category': issue_data.get('Category', 'General'),
            'severity': issue_data.get('Severity', 'medium'),
            'type': workflow_type,
            'created_at': datetime.now().isoformat(),
            'steps': []
        }

        # Extract implementation steps
        impl_steps = issue_data.get('Implementation_Steps', '')
        if isinstance(impl_steps, str) and impl_steps:
            try:
                steps = json.loads(impl_steps)
            except json.JSONDecodeError:
                steps = impl_steps.split('\n')
        elif isinstance(impl_steps, list):
            steps = impl_steps
        else:
            steps = ['Manual intervention required']

        # Generate steps based on type
        if workflow_type == 'bash':
            workflow['steps'] = self._generate_bash_steps(issue_data, steps)
        elif workflow_type == 'python':
            workflow['steps'] = self._generate_python_steps(issue_data, steps)
        elif workflow_type == 'ansible':
            workflow['steps'] = self._generate_ansible_steps(issue_data, steps)
        elif workflow_type == 'docker':
            workflow['steps'] = self._generate_docker_steps(issue_data, steps)
        else:
            raise ValueError(f"Unsupported workflow type: {workflow_type}")

        return workflow

    def _generate_bash_steps(self, issue_data: Dict[str, Any],
                            steps: List[str]) -> List[Dict[str, Any]]:
        """Generate bash workflow steps"""
        bash_steps = []

        category = issue_data.get('Category', '').lower()
        issue_type = issue_data.get('Issue_Type', '').lower()

        # Pre-check step
        bash_steps.append({
            'name': 'Pre-check',
            'command': 'echo "Starting automated fix..."',
            'description': 'Initial validation'
        })

        # Main fix steps based on category
        if 'memory' in category or 'memory' in issue_type:
            bash_steps.append({
                'name': 'Check memory usage',
                'command': 'free -h && ps aux --sort=-%mem | head -n 10',
                'description': 'Identify high memory processes'
            })
            bash_steps.append({
                'name': 'Clear caches',
                'command': 'sync && echo 3 > /proc/sys/vm/drop_caches',
                'description': 'Clear system caches'
            })

        elif 'cpu' in category or 'cpu' in issue_type:
            bash_steps.append({
                'name': 'Check CPU usage',
                'command': 'top -b -n 1 | head -n 20',
                'description': 'Identify high CPU processes'
            })

        elif 'zombie' in category or 'zombie' in issue_type:
            bash_steps.append({
                'name': 'Find zombie processes',
                'command': 'ps aux | grep Z',
                'description': 'List zombie processes'
            })
            bash_steps.append({
                'name': 'Clean zombies',
                'command': 'kill -9 $(ps -A -ostat,ppid | awk \'/[zZ]/{print $2}\')',
                'description': 'Kill parent processes'
            })

        elif 'latency' in category or 'latency' in issue_type:
            bash_steps.append({
                'name': 'Check network latency',
                'command': 'ping -c 5 google.com',
                'description': 'Test network connectivity'
            })

        # Add custom steps
        for idx, step in enumerate(steps, 1):
            if step and step != 'Manual intervention required':
                bash_steps.append({
                    'name': f'Step {idx}',
                    'command': step,
                    'description': f'Custom step: {step[:50]}'
                })

        # Verification step
        bash_steps.append({
            'name': 'Verify fix',
            'command': 'echo "Fix completed. Please verify manually."',
            'description': 'Verification step'
        })

        return bash_steps

    def _generate_python_steps(self, issue_data: Dict[str, Any],
                              steps: List[str]) -> List[Dict[str, Any]]:
        """Generate Python workflow steps"""
        py_steps = []

        category = issue_data.get('Category', '').lower()

        # Import step
        py_steps.append({
            'name': 'Import modules',
            'code': 'import psutil\nimport logging\nimport sys',
            'description': 'Import required modules'
        })

        # Main fix logic
        if 'memory' in category:
            py_steps.append({
                'name': 'Check memory',
                'code': 'memory = psutil.virtual_memory()\nlogger.info(f"Memory usage: {memory.percent}%")',
                'description': 'Check memory usage'
            })

        elif 'cpu' in category:
            py_steps.append({
                'name': 'Check CPU',
                'code': 'cpu = psutil.cpu_percent(interval=1)\nlogger.info(f"CPU usage: {cpu}%")',
                'description': 'Check CPU usage'
            })

        # Add custom steps
        for idx, step in enumerate(steps, 1):
            if step and step != 'Manual intervention required':
                py_steps.append({
                    'name': f'Custom step {idx}',
                    'code': f'# {step}',
                    'description': step[:50]
                })

        return py_steps

    def _generate_ansible_steps(self, issue_data: Dict[str, Any],
                               steps: List[str]) -> List[Dict[str, Any]]:
        """Generate Ansible workflow steps"""
        ansible_steps = []

        category = issue_data.get('Category', '').lower()

        if 'service' in category or 'restart' in str(steps).lower():
            ansible_steps.append({
                'name': 'Restart service',
                'module': 'systemd',
                'params': {
                    'name': 'application',
                    'state': 'restarted'
                }
            })

        # Add custom steps
        for step in steps:
            if 'restart' in step.lower():
                ansible_steps.append({
                    'name': step,
                    'module': 'systemd',
                    'params': {'state': 'restarted'}
                })
            elif 'install' in step.lower():
                ansible_steps.append({
                    'name': step,
                    'module': 'apt',
                    'params': {'name': 'package', 'state': 'present'}
                })

        return ansible_steps

    def _generate_docker_steps(self, issue_data: Dict[str, Any],
                              steps: List[str]) -> List[Dict[str, Any]]:
        """Generate Docker workflow steps"""
        docker_steps = []

        # Always include container restart
        docker_steps.append({
            'name': 'Restart container',
            'command': 'docker restart ${CONTAINER_NAME}',
            'description': 'Restart the container'
        })

        docker_steps.append({
            'name': 'Check container status',
            'command': 'docker ps -a | grep ${CONTAINER_NAME}',
            'description': 'Verify container is running'
        })

        return docker_steps

    def save_workflow(self, workflow: Dict[str, Any],
                     filename: Optional[str] = None) -> str:
        """
        Save workflow to file

        Args:
            workflow: Workflow specification
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            filename = f"{workflow['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = self.output_dir / filename

        with open(output_path, 'w') as f:
            json.dump(workflow, f, indent=2)

        logger.info(f"Workflow saved to {output_path}")
        return str(output_path)

    def generate_script(self, workflow: Dict[str, Any]) -> str:
        """
        Generate executable script from workflow

        Args:
            workflow: Workflow specification

        Returns:
            Script content as string
        """
        workflow_type = workflow.get('type', 'bash')

        if workflow_type == 'bash':
            return self._generate_bash_script(workflow)
        elif workflow_type == 'python':
            return self._generate_python_script(workflow)
        elif workflow_type == 'ansible':
            return self._generate_ansible_playbook(workflow)
        else:
            raise ValueError(f"Unsupported workflow type: {workflow_type}")

    def _generate_bash_script(self, workflow: Dict[str, Any]) -> str:
        """Generate bash script from workflow"""
        script = f"""#!/bin/bash
# Workflow: {workflow['name']}
# Description: {workflow['description']}
# Generated: {workflow['created_at']}

set -e  # Exit on error

echo "=== {workflow['name']} ==="
echo "Description: {workflow['description']}"
echo "Severity: {workflow['severity']}"
echo ""

"""

        for step in workflow['steps']:
            script += f"# {step['name']}: {step['description']}\n"
            script += f"echo \"Executing: {step['name']}\"\n"
            script += f"{step['command']}\n"
            script += "echo \"\"\n\n"

        script += 'echo "Workflow completed successfully"\n'

        return script

    def _generate_python_script(self, workflow: Dict[str, Any]) -> str:
        """Generate Python script from workflow"""
        script = f"""#!/usr/bin/env python3
\"\"\"
Workflow: {workflow['name']}
Description: {workflow['description']}
Generated: {workflow['created_at']}
\"\"\"

import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    \"\"\"Execute workflow\"\"\"
    logger.info("Starting workflow: {workflow['name']}")
    logger.info("Description: {workflow['description']}")
    logger.info("Severity: {workflow['severity']}")

"""

        for step in workflow['steps']:
            script += f"\n    # {step['name']}: {step['description']}\n"
            script += f"    logger.info('Executing: {step['name']}')\n"
            script += f"    {step.get('code', '# TODO')}\n"

        script += """
    logger.info("Workflow completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""

        return script

    def _generate_ansible_playbook(self, workflow: Dict[str, Any]) -> str:
        """Generate Ansible playbook from workflow"""
        playbook = {
            'name': workflow['name'],
            'hosts': 'all',
            'become': True,
            'tasks': []
        }

        for step in workflow['steps']:
            task = {
                'name': step['name'],
                step.get('module', 'shell'): step.get('params', {})
            }
            playbook['tasks'].append(task)

        return yaml.dump([playbook], default_flow_style=False)

    def generate_dockerfile(self, workflow: Dict[str, Any]) -> str:
        """
        Generate Dockerfile to containerize workflow

        Args:
            workflow: Workflow specification

        Returns:
            Dockerfile content
        """
        base_image = 'python:3.9-slim' if workflow['type'] == 'python' else 'ubuntu:22.04'

        dockerfile = f"""FROM {base_image}

# Workflow: {workflow['name']}
# Generated: {datetime.now().isoformat()}

LABEL description="{workflow['description']}"
LABEL severity="{workflow['severity']}"

WORKDIR /app

"""

        if workflow['type'] == 'python':
            dockerfile += """RUN pip install --no-cache-dir psutil

COPY workflow_script.py /app/

CMD ["python", "workflow_script.py"]
"""
        else:
            dockerfile += """RUN apt-get update && apt-get install -y procps net-tools

COPY workflow_script.sh /app/
RUN chmod +x /app/workflow_script.sh

CMD ["/app/workflow_script.sh"]
"""

        return dockerfile

    def export_workflow_bundle(self, workflow: Dict[str, Any],
                              bundle_dir: Optional[str] = None) -> str:
        """
        Export complete workflow bundle with scripts and Dockerfile

        Args:
            workflow: Workflow specification
            bundle_dir: Optional custom bundle directory

        Returns:
            Path to bundle directory
        """
        if bundle_dir is None:
            bundle_dir = self.output_dir / workflow['name']

        bundle_path = Path(bundle_dir)
        bundle_path.mkdir(parents=True, exist_ok=True)

        # Save workflow spec
        with open(bundle_path / 'workflow.json', 'w') as f:
            json.dump(workflow, f, indent=2)

        # Generate and save script
        script = self.generate_script(workflow)
        script_name = 'workflow_script.py' if workflow['type'] == 'python' else 'workflow_script.sh'
        script_path = bundle_path / script_name
        script_path.write_text(script)
        script_path.chmod(0o755)

        # Generate Dockerfile
        dockerfile = self.generate_dockerfile(workflow)
        (bundle_path / 'Dockerfile').write_text(dockerfile)

        # Generate README
        readme = f"""# {workflow['name']}

**Description:** {workflow['description']}
**Category:** {workflow['category']}
**Severity:** {workflow['severity']}
**Generated:** {workflow['created_at']}

## Usage

### Run directly:
```bash
./{script_name}
```

### Run in Docker:
```bash
docker build -t {workflow['name']} .
docker run {workflow['name']}
```

## Steps

"""
        for idx, step in enumerate(workflow['steps'], 1):
            readme += f"{idx}. **{step['name']}**: {step['description']}\n"

        (bundle_path / 'README.md').write_text(readme)

        logger.info(f"Workflow bundle exported to {bundle_path}")
        return str(bundle_path)
