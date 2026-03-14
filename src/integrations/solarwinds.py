"""
SolarWinds Log & Event Manager Integration.

Connects to SolarWinds LEM (formerly SIEM) for log aggregation,
event correlation, and security monitoring.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class SolarWindsIntegration(BaseIntegration):
    """
    Integration with SolarWinds Log & Event Manager (LEM).

    Features:
    - Log aggregation and search
    - Event correlation
    - Security event monitoring
    - Compliance reporting
    - Connection pooling with retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SolarWinds LEM integration.

        Args:
            config: Configuration dict with:
                - api_url: SolarWinds LEM API URL
                - username: API username
                - password: API password
                - verify_ssl: Verify SSL certificates (default: True)
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.api_url = config.get('api_url', 'https://localhost:8080/api')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.verify_ssl = config.get('verify_ssl', True)
        self.timeout = config.get('timeout', 30)

        # Create session with auth
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        # Add retry logic
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"SolarWinds LEM integration initialized: {self.api_url}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from SolarWinds LEM.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (node_id, log_type, severity)

        Returns:
            List of LogEntry objects
        """
        url = f"{self.api_url}/events/search"

        payload = {
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'maxResults': filters.get('max_results', 1000) if filters else 1000
        }

        if filters:
            if 'node_id' in filters:
                payload['nodeId'] = filters['node_id']
            if 'log_type' in filters:
                payload['logType'] = filters['log_type']
            if 'severity' in filters:
                payload['severity'] = filters['severity']
            if 'query' in filters:
                payload['filter'] = filters['query']

        logs = []

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            for event in data.get('events', []):
                log = LogEntry(
                    timestamp=datetime.fromtimestamp(event.get('timestamp', 0) / 1000),
                    message=event.get('message', ''),
                    level=self._map_severity(event.get('severity', 'INFO')),
                    source='solarwinds_lem',
                    metadata={
                        'event_id': event.get('eventId'),
                        'node_id': event.get('nodeId'),
                        'node_name': event.get('nodeName'),
                        'log_type': event.get('logType'),
                        'severity': event.get('severity'),
                        'source_ip': event.get('sourceIp'),
                        'destination_ip': event.get('destinationIp'),
                        'user': event.get('user'),
                        'category': event.get('category'),
                        'correlation_id': event.get('correlationId')
                    }
                )
                logs.append(log)

            logger.info(f"Fetched {len(logs)} logs from SolarWinds LEM")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching SolarWinds LEM logs: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error and security events from SolarWinds LEM.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        if filters:
            filters = filters.copy()
        else:
            filters = {}

        # Filter for high severity events
        filters['severity'] = ['Critical', 'High', 'Error']

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from SolarWinds LEM.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            List of PerformanceMetric objects
        """
        url = f"{self.api_url}/metrics"

        params = {
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000)
        }

        if metric_names:
            params['metricNames'] = ','.join(metric_names)

        metrics = []

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            for metric_data in data.get('metrics', []):
                metric = PerformanceMetric(
                    metric_name=metric_data.get('name', 'unknown'),
                    value=float(metric_data.get('value', 0)),
                    unit=metric_data.get('unit', 'unknown'),
                    timestamp=datetime.fromtimestamp(metric_data.get('timestamp', 0) / 1000),
                    dimensions={
                        'node_id': metric_data.get('nodeId'),
                        'node_name': metric_data.get('nodeName')
                    }
                )
                metrics.append(metric)

            logger.info(f"Fetched {len(metrics)} metrics from SolarWinds LEM")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching SolarWinds LEM metrics: {e}")

        return metrics

    def get_security_events(
        self,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get security events from SolarWinds LEM.

        Args:
            start_time: Start of time range
            end_time: End of time range
            event_type: Optional event type filter

        Returns:
            List of security event dictionaries
        """
        url = f"{self.api_url}/security/events"

        payload = {
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000)
        }

        if event_type:
            payload['eventType'] = event_type

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            events = data.get('events', [])
            logger.info(f"Retrieved {len(events)} security events from SolarWinds LEM")
            return events

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching security events: {e}")
            return []

    def get_correlation_rules(self) -> List[Dict[str, Any]]:
        """
        Get active correlation rules.

        Returns:
            List of correlation rule dictionaries
        """
        url = f"{self.api_url}/correlation/rules"

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            rules = data.get('rules', [])
            logger.info(f"Retrieved {len(rules)} correlation rules from SolarWinds LEM")
            return rules

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching correlation rules: {e}")
            return []

    def _map_severity(self, severity: str) -> str:
        """Map SolarWinds severity to standard log level."""
        severity_map = {
            'critical': 'CRITICAL',
            'high': 'ERROR',
            'medium': 'WARNING',
            'low': 'INFO',
            'informational': 'INFO',
            'debug': 'DEBUG'
        }
        return severity_map.get(severity.lower(), 'INFO')

    def test_connection(self) -> bool:
        """Test connection to SolarWinds LEM API."""
        try:
            url = f"{self.api_url}/status"
            response = self.session.get(
                url,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            logger.info("SolarWinds LEM connection test: SUCCESS")
            return True
        except Exception as e:
            logger.error(f"SolarWinds LEM connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
