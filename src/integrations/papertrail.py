"""
Papertrail Integration for Log Retrieval.

Connects to Papertrail HTTP API for log search and retrieval.
Supports real-time log streaming and historical search.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class PapertrailIntegration(BaseIntegration):
    """
    Integration with Papertrail for log retrieval and search.

    Features:
    - Log search with full-text queries
    - System and group filtering
    - Real-time log streaming
    - Connection pooling
    - Automatic retry with exponential backoff
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Papertrail integration.

        Args:
            config: Configuration dict with:
                - api_token: Papertrail API token
                - api_url: API URL (default: 'https://papertrailapp.com/api/v1')
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.api_token = config.get('api_token', '')
        self.api_url = config.get('api_url', 'https://papertrailapp.com/api/v1')
        self.timeout = config.get('timeout', 30)

        # Create session with auth header
        self.session = requests.Session()
        self.session.headers.update({
            'X-Papertrail-Token': self.api_token,
            'Accept': 'application/json'
        })

        # Add retry logic
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info("Papertrail integration initialized")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Papertrail.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (query, system_id, group_id)

        Returns:
            List of LogEntry objects
        """
        url = f"{self.api_url}/events/search.json"

        params = {
            'min_time': int(start_time.timestamp()),
            'max_time': int(end_time.timestamp())
        }

        if filters:
            if 'query' in filters:
                params['q'] = filters['query']
            if 'system_id' in filters:
                params['system_id'] = filters['system_id']
            if 'group_id' in filters:
                params['group_id'] = filters['group_id']

        logs = []

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            for event in data.get('events', []):
                log = LogEntry(
                    timestamp=datetime.fromisoformat(event.get('received_at', '').replace('Z', '+00:00')),
                    message=event.get('message', ''),
                    level=self._infer_level(event.get('severity', 'info')),
                    source='papertrail',
                    metadata={
                        'hostname': event.get('hostname'),
                        'program': event.get('program'),
                        'facility': event.get('facility'),
                        'severity': event.get('severity'),
                        'source_ip': event.get('source_ip'),
                        'source_id': event.get('source_id')
                    }
                )
                logs.append(log)

            logger.info(f"Fetched {len(logs)} logs from Papertrail")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Papertrail logs: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error logs from Papertrail.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        if filters:
            filters = filters.copy()
            error_query = 'error OR ERROR OR exception OR critical OR CRITICAL OR failed'
            if 'query' in filters:
                filters['query'] = f"{filters['query']} {error_query}"
            else:
                filters['query'] = error_query
        else:
            filters = {'query': 'error OR ERROR OR exception OR critical OR CRITICAL OR failed'}

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Papertrail primarily stores logs, not metrics.
        This method returns empty list but can be extended to parse metrics from logs.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            Empty list (Papertrail is log-focused)
        """
        logger.info("Papertrail doesn't natively support metrics - use log queries instead")
        return []

    def _infer_level(self, severity: str) -> str:
        """Convert Papertrail severity to standard log level."""
        severity_map = {
            'emergency': 'CRITICAL',
            'alert': 'CRITICAL',
            'critical': 'CRITICAL',
            'error': 'ERROR',
            'warning': 'WARNING',
            'warn': 'WARNING',
            'notice': 'INFO',
            'info': 'INFO',
            'informational': 'INFO',
            'debug': 'DEBUG'
        }
        return severity_map.get(severity.lower(), 'INFO')

    def get_systems(self) -> List[Dict[str, Any]]:
        """
        Get list of systems (hosts) in Papertrail.

        Returns:
            List of system dictionaries
        """
        url = f"{self.api_url}/systems.json"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            systems = response.json()
            logger.info(f"Retrieved {len(systems)} systems from Papertrail")
            return systems

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Papertrail systems: {e}")
            return []

    def test_connection(self) -> bool:
        """Test connection to Papertrail API."""
        try:
            url = f"{self.api_url}/systems.json"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            logger.info("Papertrail connection test: SUCCESS")
            return True
        except Exception as e:
            logger.error(f"Papertrail connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
