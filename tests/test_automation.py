"""
Tests for Automation Module
"""

import pytest
import json
from datetime import datetime
from pathlib import Path

from src.automation.script_templates import ScriptTemplates
from src.automation.workflow_generator import WorkflowGenerator
from src.automation.automation_engine import AutomationEngine


class TestScriptTemplates:
    """Test ScriptTemplates class"""

    def test_bash_template(self):
        """Test bash template generation"""
        commands = ['echo "test"', 'ls -la']
        script = ScriptTemplates.bash_template('test_issue', commands)

        assert '#!/bin/bash' in script
        assert 'test_issue' in script
        assert 'echo "test"' in script
        assert 'ls -la' in script

    def test_python_template(self):
        """Test Python template generation"""
        fix_code = 'print("fixing issue")'
        script = ScriptTemplates.python_template('test_issue', fix_code)

        assert '#!/usr/bin/env python3' in script
        assert 'test_issue' in script
        assert 'print("fixing issue")' in script

    def test_memory_leak_fix(self):
        """Test memory leak fix template"""
        templates = ScriptTemplates.memory_leak_fix()

        assert 'bash' in templates
        assert 'python' in templates
        assert 'memory' in templates['bash'].lower()

    def test_high_cpu_fix(self):
        """Test high CPU fix template"""
        templates = ScriptTemplates.high_cpu_fix()

        assert 'bash' in templates
        assert 'python' in templates
        assert 'cpu' in templates['bash'].lower()

    def test_zombie_process_fix(self):
        """Test zombie process fix template"""
        templates = ScriptTemplates.zombie_process_fix()

        assert 'bash' in templates
        assert 'python' in templates
        assert 'zombie' in templates['bash'].lower()

    def test_get_template(self):
        """Test getting template by issue type"""
        template = ScriptTemplates.get_template('memory_leak', 'bash')

        assert template is not None
        assert 'memory' in template.lower()


class TestWorkflowGenerator:
    """Test WorkflowGenerator class"""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create workflow generator instance"""
        return WorkflowGenerator(str(tmp_path / 'workflows'))

    @pytest.fixture
    def sample_issue(self):
        """Create sample issue data"""
        return {
            'Error_Pattern': 'Memory leak in application',
            'Category': 'Memory',
            'Severity': 'critical',
            'Issue_Type': 'memory_leak',
            'Solution': 'Restart service and clear caches',
            'Implementation_Steps': json.dumps([
                'Check memory usage',
                'Identify leaking process',
                'Restart service'
            ])
        }

    def test_generate_workflow_bash(self, generator, sample_issue):
        """Test bash workflow generation"""
        workflow = generator.generate_workflow(sample_issue, 'bash')

        assert workflow['type'] == 'bash'
        assert 'steps' in workflow
        assert len(workflow['steps']) > 0
        assert workflow['category'] == 'Memory'
        assert workflow['severity'] == 'critical'

    def test_generate_workflow_python(self, generator, sample_issue):
        """Test Python workflow generation"""
        workflow = generator.generate_workflow(sample_issue, 'python')

        assert workflow['type'] == 'python'
        assert 'steps' in workflow
        assert len(workflow['steps']) > 0

    def test_generate_workflow_ansible(self, generator, sample_issue):
        """Test Ansible workflow generation"""
        workflow = generator.generate_workflow(sample_issue, 'ansible')

        assert workflow['type'] == 'ansible'
        assert 'steps' in workflow

    def test_generate_workflow_docker(self, generator, sample_issue):
        """Test Docker workflow generation"""
        workflow = generator.generate_workflow(sample_issue, 'docker')

        assert workflow['type'] == 'docker'
        assert 'steps' in workflow

    def test_save_workflow(self, generator, sample_issue):
        """Test saving workflow"""
        workflow = generator.generate_workflow(sample_issue, 'bash')
        path = generator.save_workflow(workflow)

        assert Path(path).exists()

        # Verify content
        with open(path) as f:
            saved_workflow = json.load(f)
            assert saved_workflow['name'] == workflow['name']

    def test_generate_bash_script(self, generator, sample_issue):
        """Test bash script generation"""
        workflow = generator.generate_workflow(sample_issue, 'bash')
        script = generator.generate_script(workflow)

        assert '#!/bin/bash' in script
        assert workflow['name'] in script
        assert 'set -e' in script

    def test_generate_python_script(self, generator, sample_issue):
        """Test Python script generation"""
        workflow = generator.generate_workflow(sample_issue, 'python')
        script = generator.generate_script(workflow)

        assert '#!/usr/bin/env python3' in script
        assert 'import logging' in script
        assert 'def main()' in script

    def test_generate_dockerfile(self, generator, sample_issue):
        """Test Dockerfile generation"""
        workflow = generator.generate_workflow(sample_issue, 'python')
        dockerfile = generator.generate_dockerfile(workflow)

        assert 'FROM' in dockerfile
        assert 'WORKDIR' in dockerfile
        assert 'CMD' in dockerfile

    def test_export_workflow_bundle(self, generator, sample_issue, tmp_path):
        """Test workflow bundle export"""
        workflow = generator.generate_workflow(sample_issue, 'bash')
        bundle_path = generator.export_workflow_bundle(
            workflow,
            str(tmp_path / 'bundle')
        )

        bundle_dir = Path(bundle_path)
        assert bundle_dir.exists()
        assert (bundle_dir / 'workflow.json').exists()
        assert (bundle_dir / 'Dockerfile').exists()
        assert (bundle_dir / 'README.md').exists()

        # Check script file
        script_files = list(bundle_dir.glob('workflow_script.*'))
        assert len(script_files) > 0


class TestAutomationEngine:
    """Test AutomationEngine class"""

    @pytest.fixture
    def engine(self):
        """Create automation engine instance"""
        return AutomationEngine(dry_run=True)

    @pytest.fixture
    def sample_workflow(self):
        """Create sample workflow"""
        return {
            'name': 'test_workflow',
            'description': 'Test workflow',
            'type': 'bash',
            'severity': 'medium',
            'steps': [
                {
                    'name': 'Step 1',
                    'command': 'echo "test"',
                    'description': 'Test step'
                },
                {
                    'name': 'Step 2',
                    'command': 'ls -la',
                    'description': 'List files'
                }
            ]
        }

    def test_execute_workflow_sync(self, engine, sample_workflow):
        """Test synchronous workflow execution"""
        result = engine.execute_workflow(sample_workflow, async_execution=False)

        assert 'execution_id' in result
        assert 'status' in result
        assert result['total_steps'] == 2
        assert result['steps_completed'] >= 0

    def test_execute_workflow_async(self, engine, sample_workflow):
        """Test asynchronous workflow execution"""
        result = engine.execute_workflow(sample_workflow, async_execution=True)

        assert 'execution_id' in result
        assert result['execution_id'] in engine.active_executions

    def test_execute_workflow_dry_run(self, engine, sample_workflow):
        """Test dry run mode"""
        result = engine.execute_workflow(sample_workflow)

        assert result['status'] in ['running', 'completed']

        # Check that steps contain dry run indicators
        for step_result in result.get('step_results', []):
            assert '[DRY RUN]' in step_result.get('output', '')

    def test_get_execution_status(self, engine, sample_workflow):
        """Test getting execution status"""
        result = engine.execute_workflow(sample_workflow)
        execution_id = result['execution_id']

        status = engine.get_execution_status(execution_id)

        assert status is not None
        assert status['execution_id'] == execution_id

    def test_get_execution_history(self, engine, sample_workflow):
        """Test getting execution history"""
        engine.execute_workflow(sample_workflow)

        history = engine.get_execution_history(limit=10)

        assert isinstance(history, list)
        assert len(history) > 0

    def test_save_execution_log(self, engine, sample_workflow, tmp_path):
        """Test saving execution log"""
        result = engine.execute_workflow(sample_workflow)
        execution_id = result['execution_id']

        log_file = tmp_path / 'execution.json'
        success = engine.save_execution_log(execution_id, str(log_file))

        assert success is True
        assert log_file.exists()

    def test_clear_history(self, engine, sample_workflow):
        """Test clearing old history"""
        engine.execute_workflow(sample_workflow)

        cleared = engine.clear_history(older_than_days=0)

        assert cleared >= 0


class TestIntegration:
    """Integration tests for automation module"""

    @pytest.fixture
    def full_setup(self, tmp_path):
        """Set up full automation pipeline"""
        generator = WorkflowGenerator(str(tmp_path / 'workflows'))
        engine = AutomationEngine(dry_run=True)

        return generator, engine

    @pytest.fixture
    def complex_issue(self):
        """Create complex issue with multiple steps"""
        return {
            'Error_Pattern': 'High memory usage with zombie processes',
            'Category': 'Memory',
            'Severity': 'critical',
            'Issue_Type': 'memory_leak_with_zombies',
            'Solution': 'Clean up zombies and restart services',
            'Implementation_Steps': json.dumps([
                'Identify zombie processes',
                'Kill parent processes',
                'Clear memory caches',
                'Restart affected services',
                'Verify system health'
            ])
        }

    def test_full_workflow_pipeline(self, full_setup, complex_issue):
        """Test complete workflow from generation to execution"""
        generator, engine = full_setup

        # Generate workflow
        workflow = generator.generate_workflow(complex_issue, 'bash')

        assert workflow is not None
        assert len(workflow['steps']) > 0

        # Save workflow
        workflow_path = generator.save_workflow(workflow)
        assert Path(workflow_path).exists()

        # Generate script
        script = generator.generate_script(workflow)
        assert '#!/bin/bash' in script

        # Execute workflow (dry run)
        result = engine.execute_workflow(workflow)

        assert result['status'] in ['running', 'completed', 'failed']
        assert result['total_steps'] == len(workflow['steps'])

    def test_export_and_containerize(self, full_setup, complex_issue, tmp_path):
        """Test exporting workflow bundle for containerization"""
        generator, engine = full_setup

        # Generate workflow
        workflow = generator.generate_workflow(complex_issue, 'python')

        # Export bundle
        bundle_path = generator.export_workflow_bundle(
            workflow,
            str(tmp_path / 'bundle')
        )

        bundle_dir = Path(bundle_path)

        # Verify all required files exist
        assert (bundle_dir / 'workflow.json').exists()
        assert (bundle_dir / 'Dockerfile').exists()
        assert (bundle_dir / 'README.md').exists()
        assert (bundle_dir / 'workflow_script.py').exists()

        # Verify Dockerfile content
        dockerfile_content = (bundle_dir / 'Dockerfile').read_text()
        assert 'FROM python' in dockerfile_content
        assert 'workflow_script.py' in dockerfile_content
