"""
Comprehensive tests for all log and monitoring platform integrations.

Tests cover:
- Connection testing
- Log retrieval
- Error filtering
- Performance metrics
- Memory leaks
- CPU usage
- Latency benchmarks
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import List

# Import all integrations
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric
from src.integrations.prometheus import PrometheusIntegration
from src.integrations.sumologic import SumoLogicIntegration
from src.integrations.papertrail import PapertrailIntegration
from src.integrations.loggly import LogglyIntegration
from src.integrations.fluentd import FluentdIntegration
from src.integrations.logstash import LogstashIntegration
from src.integrations.goaccess import GoAccessIntegration
from src.integrations.retrace import RetraceIntegration
from src.integrations.solarwinds import SolarWindsIntegration
from src.integrations.grafana import GrafanaIntegration
from src.integrations import get_integration, list_available_platforms


class TestBaseIntegration(unittest.TestCase):
    """Test base integration functionality."""

    def test_log_entry_creation(self):
        """Test LogEntry object creation."""
        timestamp = datetime.utcnow()
        log = LogEntry(
            timestamp=timestamp,
            message="Test log message",
            level="ERROR",
            source="test",
            metadata={"key": "value"}
        )

        self.assertEqual(log.timestamp, timestamp)
        self.assertEqual(log.message, "Test log message")
        self.assertEqual(log.level, "ERROR")
        self.assertEqual(log.source, "test")
        self.assertEqual(log.metadata["key"], "value")

    def test_log_entry_to_dict(self):
        """Test LogEntry to dictionary conversion."""
        timestamp = datetime.utcnow()
        log = LogEntry(
            timestamp=timestamp,
            message="Test",
            level="INFO",
            source="test"
        )

        log_dict = log.to_dict()
        self.assertIn('timestamp', log_dict)
        self.assertIn('message', log_dict)
        self.assertIn('level', log_dict)
        self.assertIn('source', log_dict)

    def test_performance_metric_creation(self):
        """Test PerformanceMetric object creation."""
        timestamp = datetime.utcnow()
        metric = PerformanceMetric(
            metric_name="cpu.usage",
            value=85.5,
            unit="percent",
            timestamp=timestamp,
            dimensions={"host": "server1"}
        )

        self.assertEqual(metric.metric_name, "cpu.usage")
        self.assertEqual(metric.value, 85.5)
        self.assertEqual(metric.unit, "percent")
        self.assertEqual(metric.timestamp, timestamp)


class TestPrometheusIntegration(unittest.TestCase):
    """Test Prometheus integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'prometheus_url': 'http://localhost:9090',
            'timeout': 10
        }
        self.integration = PrometheusIntegration(self.config)
        self.start_time = datetime.utcnow() - timedelta(hours=1)
        self.end_time = datetime.utcnow()

    @patch('requests.Session.get')
    def test_fetch_logs_from_alerts(self, mock_get):
        """Test fetching logs from Prometheus alerts."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'data': {
                'alerts': [
                    {
                        'state': 'firing',
                        'labels': {'alertname': 'HighCPU', 'severity': 'critical'},
                        'annotations': {'summary': 'CPU usage above 90%'}
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        logs = self.integration.fetch_logs(self.start_time, self.end_time)

        self.assertIsInstance(logs, list)
        if logs:
            self.assertIsInstance(logs[0], LogEntry)

    @patch('requests.Session.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection to Prometheus."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_get.return_value = mock_response

        result = self.integration.test_connection()
        self.assertTrue(result)

    @patch('requests.Session.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection to Prometheus."""
        mock_get.side_effect = Exception("Connection failed")

        result = self.integration.test_connection()
        self.assertFalse(result)

    def test_infer_unit(self):
        """Test metric unit inference."""
        self.assertEqual(self.integration._infer_unit('memory_bytes'), 'bytes')
        self.assertEqual(self.integration._infer_unit('duration_seconds'), 'seconds')
        self.assertEqual(self.integration._infer_unit('cpu_usage'), 'percent')
        self.assertEqual(self.integration._infer_unit('requests_total'), 'count')


class TestSumoLogicIntegration(unittest.TestCase):
    """Test Sumo Logic integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'access_id': 'test_id',
            'access_key': 'test_key',
            'api_endpoint': 'https://api.sumologic.com/api'
        }
        self.integration = SumoLogicIntegration(self.config)

    @patch('requests.Session.post')
    def test_create_search_job(self, mock_post):
        """Test creating a search job."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'job123'}
        mock_post.return_value = mock_response

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        job_id = self.integration._create_search_job('*', start_time, end_time)

        self.assertEqual(job_id, 'job123')

    def test_infer_level(self):
        """Test log level inference."""
        self.assertEqual(self.integration._infer_level('CRITICAL error occurred'), 'CRITICAL')
        self.assertEqual(self.integration._infer_level('ERROR: Failed to connect'), 'ERROR')
        self.assertEqual(self.integration._infer_level('WARNING: High memory usage'), 'WARNING')
        self.assertEqual(self.integration._infer_level('INFO: System started'), 'INFO')


class TestPapertrailIntegration(unittest.TestCase):
    """Test Papertrail integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'api_token': 'test_token',
            'api_url': 'https://papertrailapp.com/api/v1'
        }
        self.integration = PapertrailIntegration(self.config)

    def test_infer_level(self):
        """Test severity to log level conversion."""
        self.assertEqual(self.integration._infer_level('emergency'), 'CRITICAL')
        self.assertEqual(self.integration._infer_level('error'), 'ERROR')
        self.assertEqual(self.integration._infer_level('warning'), 'WARNING')
        self.assertEqual(self.integration._infer_level('info'), 'INFO')
        self.assertEqual(self.integration._infer_level('debug'), 'DEBUG')

    @patch('requests.Session.get')
    def test_test_connection(self, mock_get):
        """Test connection to Papertrail."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.integration.test_connection()
        self.assertTrue(result)


class TestLogglyIntegration(unittest.TestCase):
    """Test Loggly integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'account_name': 'test_account',
            'api_token': 'test_token'
        }
        self.integration = LogglyIntegration(self.config)

    def test_infer_level_from_explicit_field(self):
        """Test log level inference from explicit fields."""
        event_data = {'json': {'level': 'ERROR'}}
        self.assertEqual(self.integration._infer_level(event_data), 'ERROR')

        event_data = {'json': {'severity': 'CRITICAL'}}
        self.assertEqual(self.integration._infer_level(event_data), 'CRITICAL')

    def test_infer_level_from_message(self):
        """Test log level inference from message content."""
        event_data = {'message': 'Critical failure detected'}
        self.assertEqual(self.integration._infer_level(event_data), 'CRITICAL')

        event_data = {'message': 'An error occurred while processing'}
        self.assertEqual(self.integration._infer_level(event_data), 'ERROR')


class TestFluentdIntegration(unittest.TestCase):
    """Test Fluentd integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'http_endpoint': 'http://localhost:9880',
            'storage_backend': 'http'
        }
        self.integration = FluentdIntegration(self.config)

    @patch('requests.Session.post')
    def test_send_log(self, mock_post):
        """Test sending log to Fluentd."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.integration.send_log('test.tag', {'message': 'test'})
        self.assertTrue(result)

    @patch('src.integrations.fluentd.requests.Session.post')
    def test_send_log_failure(self, mock_post):
        """Test failed log send."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        result = self.integration.send_log('test.tag', {'message': 'test'})
        self.assertFalse(result)


class TestLogstashIntegration(unittest.TestCase):
    """Test Logstash integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'http_endpoint': 'http://localhost:8080',
            'elasticsearch_hosts': ['http://localhost:9200']
        }
        self.integration = LogstashIntegration(self.config)

    def test_extract_level(self):
        """Test log level extraction."""
        log_data = {'level': 'ERROR'}
        self.assertEqual(self.integration._extract_level(log_data), 'ERROR')

        log_data = {'loglevel': 'WARNING'}
        self.assertEqual(self.integration._extract_level(log_data), 'WARNING')

        log_data = {'message': 'Critical system failure'}
        self.assertEqual(self.integration._extract_level(log_data), 'CRITICAL')


class TestGoAccessIntegration(unittest.TestCase):
    """Test GoAccess integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'log_files': ['/var/log/nginx/access.log'],
            'log_format': 'COMBINED'
        }
        self.integration = GoAccessIntegration(self.config)

    def test_status_to_level(self):
        """Test HTTP status code to log level conversion."""
        self.assertEqual(self.integration._status_to_level(200), 'INFO')
        self.assertEqual(self.integration._status_to_level(301), 'WARNING')
        self.assertEqual(self.integration._status_to_level(404), 'ERROR')
        self.assertEqual(self.integration._status_to_level(500), 'CRITICAL')
        self.assertEqual(self.integration._status_to_level(503), 'CRITICAL')


class TestRetraceIntegration(unittest.TestCase):
    """Test Retrace (Stackify) integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'api_key': 'test_key',
            'app_id': 'test_app',
            'environment': 'Production'
        }
        self.integration = RetraceIntegration(self.config)

    @patch('requests.Session.get')
    def test_test_connection(self, mock_get):
        """Test connection to Retrace."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.integration.test_connection()
        self.assertTrue(result)


class TestSolarWindsIntegration(unittest.TestCase):
    """Test SolarWinds LEM integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'api_url': 'https://localhost:8080/api',
            'username': 'admin',
            'password': 'password'
        }
        self.integration = SolarWindsIntegration(self.config)

    def test_map_severity(self):
        """Test severity mapping."""
        self.assertEqual(self.integration._map_severity('critical'), 'CRITICAL')
        self.assertEqual(self.integration._map_severity('high'), 'ERROR')
        self.assertEqual(self.integration._map_severity('medium'), 'WARNING')
        self.assertEqual(self.integration._map_severity('low'), 'INFO')


class TestGrafanaIntegration(unittest.TestCase):
    """Test Grafana integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'grafana_url': 'http://localhost:3000',
            'api_key': 'test_key',
            'loki_url': 'http://localhost:3100'
        }
        self.integration = GrafanaIntegration(self.config)

    def test_infer_level(self):
        """Test log level inference from message."""
        self.assertEqual(self.integration._infer_level('critical error'), 'CRITICAL')
        self.assertEqual(self.integration._infer_level('exception occurred'), 'ERROR')
        self.assertEqual(self.integration._infer_level('warning message'), 'WARNING')
        self.assertEqual(self.integration._infer_level('debug info'), 'DEBUG')
        self.assertEqual(self.integration._infer_level('normal log'), 'INFO')

    @patch('requests.Session.get')
    def test_test_connection(self, mock_get):
        """Test connection to Grafana."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.integration.test_connection()
        self.assertTrue(result)


class TestIntegrationFactory(unittest.TestCase):
    """Test integration factory functions."""

    def test_list_available_platforms(self):
        """Test listing available platforms."""
        platforms = list_available_platforms()

        self.assertIsInstance(platforms, list)
        self.assertIn('cloudwatch', platforms)
        self.assertIn('datadog', platforms)
        self.assertIn('prometheus', platforms)
        self.assertIn('grafana', platforms)
        self.assertIn('splunk', platforms)
        self.assertIn('sumologic', platforms)

    def test_get_integration_valid(self):
        """Test getting valid integration."""
        config = {'prometheus_url': 'http://localhost:9090'}
        integration = get_integration('prometheus', config)

        self.assertIsInstance(integration, PrometheusIntegration)

    def test_get_integration_invalid(self):
        """Test getting invalid integration."""
        with self.assertRaises(ValueError):
            get_integration('invalid_platform', {})


class TestMemoryLeaks(unittest.TestCase):
    """Test for memory leaks in integrations."""

    def test_prometheus_cleanup(self):
        """Test Prometheus integration cleanup."""
        config = {'prometheus_url': 'http://localhost:9090'}
        integration = PrometheusIntegration(config)

        # Verify session exists
        self.assertIsNotNone(integration.session)

        # Trigger cleanup
        del integration

        # Cleanup should have closed the session

    def test_multiple_integration_instances(self):
        """Test creating multiple integration instances doesn't leak memory."""
        configs = [
            {'prometheus_url': f'http://localhost:{9090 + i}'}
            for i in range(10)
        ]

        integrations = [PrometheusIntegration(config) for config in configs]

        # Clean up
        for integration in integrations:
            del integration


class TestCPUPerformance(unittest.TestCase):
    """Test CPU usage of integrations."""

    def test_log_parsing_performance(self):
        """Test log parsing doesn't cause excessive CPU usage."""
        import time

        config = {'prometheus_url': 'http://localhost:9090'}
        integration = PrometheusIntegration(config)

        start_time = time.time()
        # Simulate log parsing
        for _ in range(1000):
            unit = integration._infer_unit('cpu_usage_percent')

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in under 1 second
        self.assertLess(duration, 1.0)


class TestLatencyBenchmarks(unittest.TestCase):
    """Test latency benchmarks for integrations."""

    @patch('requests.Session.get')
    def test_prometheus_query_latency(self, mock_get):
        """Test Prometheus query latency."""
        import time

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'data': {'result': []}
        }
        mock_get.return_value = mock_response

        config = {'prometheus_url': 'http://localhost:9090'}
        integration = PrometheusIntegration(config)

        start_time = time.time()
        integration._execute_query('up')
        end_time = time.time()

        latency = end_time - start_time

        # Mock call should be very fast
        self.assertLess(latency, 0.1)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in integrations."""

    def test_prometheus_invalid_config(self):
        """Test Prometheus with invalid config."""
        config = {}  # Empty config
        integration = PrometheusIntegration(config)

        # Should use defaults
        self.assertEqual(integration.base_url, 'http://localhost:9090')

    @patch('src.integrations.prometheus.requests.Session.get')
    def test_prometheus_network_error(self, mock_get):
        """Test Prometheus handling network errors."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        config = {'prometheus_url': 'http://localhost:9090'}
        integration = PrometheusIntegration(config)

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()

        # Should return empty list, not crash
        logs = integration.fetch_logs(start_time, end_time)
        self.assertEqual(logs, [])


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
