"""
Tests for SOAP Integration Module
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.soap_integration import (
    RemediationAgent,
    VulnerabilityScanner,
    CertificateManager,
    ContainerLifecycleManager
)


class TestRemediationAgent:
    """Test RemediationAgent class"""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create remediation agent"""
        config = {'ansible_dir': str(tmp_path / 'ansible')}
        return RemediationAgent(config)

    def test_init(self, agent):
        """Test initialization"""
        assert agent is not None
        assert agent.kb is not None
        assert agent.workflow_gen is not None

    @patch('src.soap_integration.remediation_agent.EnhancedKnowledgeBase')
    def test_find_fix(self, mock_kb, agent):
        """Test finding fix in knowledge base"""
        # Setup mock
        mock_kb_instance = Mock()
        mock_results = MagicMock()
        mock_results.iloc = [Mock()]
        mock_results.iloc[0].get = Mock(side_effect=lambda key, default='': {
            'Error_Pattern': 'Memory leak',
            'Category': 'Memory',
            'Severity': 'critical'
        }.get(key, default))
        mock_results.__len__ = Mock(return_value=1)

        mock_kb_instance.search.return_value = mock_results
        agent.kb = mock_kb_instance

        # Execute
        fix = agent._find_fix('memory_leak')

        # Verify
        assert fix is not None
        assert fix['category'] == 'Memory'

    def test_generate_ansible_playbook(self, agent, tmp_path):
        """Test Ansible playbook generation"""
        fix = {
            'error_pattern': 'Test error',
            'category': 'Memory',
            'severity': 'high',
            'implementation_steps': json.dumps(['Step 1', 'Step 2'])
        }

        playbook_path = agent._generate_ansible_playbook(fix, 'dev')

        assert playbook_path.exists()
        assert playbook_path.suffix == '.yml'

    def test_get_target_hosts(self, agent):
        """Test getting target hosts"""
        assert agent._get_target_hosts('dev') == 'dev_servers'
        assert agent._get_target_hosts('staging') == 'staging_servers'
        assert agent._get_target_hosts('production') == 'prod_servers'

    def test_generate_memory_tasks(self, agent):
        """Test memory remediation tasks"""
        tasks = agent._generate_memory_tasks(['Clear cache', 'Restart service'])

        assert isinstance(tasks, list)
        assert len(tasks) > 0
        assert any('cache' in str(task).lower() for task in tasks)

    def test_generate_cpu_tasks(self, agent):
        """Test CPU remediation tasks"""
        tasks = agent._generate_cpu_tasks(['Reduce load'])

        assert isinstance(tasks, list)
        assert len(tasks) > 0

    def test_generate_zombie_tasks(self, agent):
        """Test zombie process remediation tasks"""
        tasks = agent._generate_zombie_tasks(['Kill zombies'])

        assert isinstance(tasks, list)
        assert len(tasks) > 0
        assert any('zombie' in str(task).lower() for task in tasks)


class TestVulnerabilityScanner:
    """Test VulnerabilityScanner class"""

    @pytest.fixture
    def scanner(self):
        """Create vulnerability scanner"""
        return VulnerabilityScanner()

    def test_init(self, scanner):
        """Test initialization"""
        assert scanner is not None
        assert scanner.scan_results == []
        assert scanner.cve_database is not None

    def test_scan_secrets(self, scanner, tmp_path):
        """Test secret scanning"""
        # Create test file with secret
        test_file = tmp_path / '.env'
        test_file.write_text('API_KEY=AKIAIOSFODNN7EXAMPLE123456')

        # Change to temp directory
        import os
        orig_dir = os.getcwd()
        os.chdir(tmp_path)

        try:
            vulnerabilities = scanner._scan_secrets()

            # Verify
            assert isinstance(vulnerabilities, list)

        finally:
            os.chdir(orig_dir)

    @patch('subprocess.run')
    def test_scan_dependencies(self, mock_run, scanner):
        """Test dependency scanning"""
        # Mock safety output
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[]'
        )

        vulnerabilities = scanner._scan_dependencies()

        assert isinstance(vulnerabilities, list)

    def test_classify_severity(self, scanner):
        """Test severity classification"""
        severity = scanner._classify_severity(None)

        assert severity in ['critical', 'high', 'medium', 'low']

    @patch('socket.create_connection')
    def test_scan_certificates(self, mock_socket, scanner):
        """Test certificate scanning"""
        # Mock SSL certificate
        mock_cert = {
            'notAfter': 'Dec 31 23:59:59 2024 GMT',
            'issuer': [('C', 'US')],
            'subject': [('CN', 'test.com')]
        }

        mock_ssl = Mock()
        mock_ssl.getpeercert.return_value = mock_cert

        vulnerabilities = scanner._scan_certificates()

        assert isinstance(vulnerabilities, list)


class TestCertificateManager:
    """Test CertificateManager class"""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create certificate manager"""
        mgr = CertificateManager()
        mgr.cert_dir = tmp_path / 'certs'
        mgr.policy_dir = tmp_path / 'policies'
        mgr.cert_dir.mkdir(parents=True, exist_ok=True)
        mgr.policy_dir.mkdir(parents=True, exist_ok=True)
        return mgr

    def test_init(self, manager):
        """Test initialization"""
        assert manager is not None
        assert manager.cert_dir.exists()
        assert manager.policy_dir.exists()

    def test_use_certbot(self, manager):
        """Test certbot detection"""
        assert manager._use_certbot('example.com') is True
        assert manager._use_certbot('internal.example.com') is False

    @patch('subprocess.run')
    def test_renew_with_certbot(self, mock_run, manager):
        """Test certbot renewal"""
        mock_run.return_value = Mock(returncode=0, stderr='')

        result = manager._renew_with_certbot('example.com')

        assert result['status'] == 'success'
        assert 'cert_path' in result

    def test_update_security_policies(self, manager):
        """Test security policy update"""
        manager._update_security_policies('example.com')

        policy_file = manager.policy_dir / 'example.com_tls_policy.json'
        assert policy_file.exists()

        with open(policy_file) as f:
            policy = json.load(f)
            assert policy['domain'] == 'example.com'
            assert policy['min_tls_version'] == '1.2'

    def test_update_security_policy(self, manager):
        """Test generic policy update"""
        policy_config = {
            'tls_version': '1.3',
            'ciphers': ['TLS_AES_256_GCM_SHA384']
        }

        success = manager.update_security_policy('test_policy', policy_config)

        assert success is True
        assert (manager.policy_dir / 'test_policy.json').exists()


class TestContainerLifecycleManager:
    """Test ContainerLifecycleManager class"""

    @pytest.fixture
    def manager(self):
        """Create container manager"""
        with patch('docker.from_env'):
            mgr = ContainerLifecycleManager()
            mgr.client = Mock()
            return mgr

    def test_init(self, manager):
        """Test initialization"""
        assert manager is not None
        assert manager.cpu_threshold == 80.0
        assert manager.memory_threshold == 85.0

    def test_check_container_health(self, manager):
        """Test container health check"""
        # Mock container
        mock_container = Mock()
        mock_container.id = 'abc123def456'
        mock_container.name = 'test_container'
        mock_container.status = 'running'
        mock_container.image.tags = ['test:latest']
        mock_container.stats.return_value = {
            'cpu_stats': {
                'cpu_usage': {'total_usage': 1000000},
                'system_cpu_usage': 2000000,
                'online_cpus': 2
            },
            'precpu_stats': {
                'cpu_usage': {'total_usage': 500000},
                'system_cpu_usage': 1000000
            },
            'memory_stats': {
                'usage': 500000000,
                'limit': 1000000000
            }
        }
        mock_container.attrs = {'State': {}}

        report = manager._check_container_health(mock_container)

        assert report['container_id'] == 'abc123def456'
        assert report['name'] == 'test_container'
        assert 'cpu_usage' in report
        assert 'memory_usage' in report

    def test_restart_containers(self, manager):
        """Test container restart"""
        # Mock containers
        mock_container1 = Mock()
        mock_container1.name = 'app_container_1'
        mock_container1.restart = Mock()

        mock_container2 = Mock()
        mock_container2.name = 'app_container_2'
        mock_container2.restart = Mock()

        manager.client.containers.list.return_value = [mock_container1, mock_container2]

        result = manager.restart_containers('app_container')

        assert result['count'] == 2
        assert len(result['restarted']) == 2
        mock_container1.restart.assert_called_once()
        mock_container2.restart.assert_called_once()

    def test_deploy_fresh_containers(self, manager):
        """Test fresh container deployment"""
        # Mock image pull and container run
        manager.client.images.pull = Mock()

        mock_container = Mock()
        mock_container.id = 'new123abc456'

        manager.client.containers.run.return_value = mock_container

        result = manager.deploy_fresh_containers('sponge:latest', count=2)

        assert result['count'] == 2
        assert len(result['deployed']) == 2
        assert manager.client.images.pull.called

    def test_get_system_resources(self, manager):
        """Test system resource retrieval"""
        resources = manager.get_system_resources()

        assert 'cpu_percent' in resources
        assert 'memory_percent' in resources
        assert 'disk_percent' in resources
        assert 'timestamp' in resources


class TestSOAPIntegration:
    """Integration tests for SOAP endpoints"""

    @pytest.fixture
    def soap_app(self):
        """Create SOAP application"""
        from src.soap_integration import create_soap_app
        return create_soap_app()

    def test_soap_app_creation(self, soap_app):
        """Test SOAP application creation"""
        assert soap_app is not None

    @patch('src.soap_integration.soap_server.EnhancedKnowledgeBase')
    def test_get_fixes_by_category(self, mock_kb):
        """Test getting fixes by category via SOAP"""
        from src.soap_integration import SpongeSOAPService

        # Setup mock
        mock_kb_instance = Mock()
        mock_results = MagicMock()
        mock_results.iterrows.return_value = [
            (0, {
                'Error_Pattern': 'Test error',
                'Category': 'Memory',
                'Severity': 'high',
                'Solution': 'Test solution',
                'Implementation_Steps': '[]',
                'Confidence': '0.9',
                'Last_Updated': '2024-01-01'
            })
        ]
        mock_kb_instance.search.return_value = mock_results

        with patch('src.knowledge_base.EnhancedKnowledgeBase', return_value=mock_kb_instance):
            service = SpongeSOAPService()
            fixes = service.get_fixes_by_category(None, 'Memory')

            assert isinstance(fixes, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
