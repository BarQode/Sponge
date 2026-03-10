"""
Grafana Integration for Metrics and Logs via Loki.

Connects to Grafana for visualization data and Loki for log aggregation.
Supports querying via Grafana API and LogQL for Loki.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class GrafanaIntegration(BaseIntegration):
    """
    Integration with Grafana for metrics visualization and Loki log aggregation.

    Features:
    - Grafana dashboard data retrieval
    - Loki log querying with LogQL
    - Prometheus metrics via Grafana
    - Alert rule status monitoring
    - Connection pooling with retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Grafana integration.

        Args:
            config: Configuration dict with:
                - grafana_url: Grafana server URL
                - api_key: Grafana API key
                - loki_url: Loki server URL (optional)
                - prometheus_url: Prometheus URL (optional)
                - verify_ssl: Verify SSL certificates (default: True)
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.grafana_url = config.get('grafana_url', 'http://localhost:3000')
        self.api_key = config.get('api_key', '')
        self.loki_url = config.get('loki_url', 'http://localhost:3100')
        self.prometheus_url = config.get('prometheus_url', 'http://localhost:9090')
        self.verify_ssl = config.get('verify_ssl', True)
        self.timeout = config.get('timeout', 30)

        # Create session with auth header
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

        # Add retry logic
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Grafana integration initialized: {self.grafana_url}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Loki via Grafana.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (query, labels)

        Returns:
            List of LogEntry objects
        """
        # Default LogQL query
        logql_query = filters.get('query', '{job="varlogs"}') if filters else '{job="varlogs"}'

        url = f"{self.loki_url}/loki/api/v1/query_range"

        params = {
            'query': logql_query,
            'start': int(start_time.timestamp() * 1e9),  # nanoseconds
            'end': int(end_time.timestamp() * 1e9),
            'limit': filters.get('limit', 1000) if filters else 1000
        }

        logs = []

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            for stream in data.get('data', {}).get('result', []):
                stream_labels = stream.get('stream', {})

                for value in stream.get('values', []):
                    timestamp_ns, log_line = value[0], value[1]

                    log = LogEntry(
                        timestamp=datetime.fromtimestamp(int(timestamp_ns) / 1e9),
                        message=log_line,
                        level=self._infer_level(log_line),
                        source='grafana_loki',
                        metadata={'labels': stream_labels}
                    )
                    logs.append(log)

            logger.info(f"Fetched {len(logs)} logs from Loki via Grafana")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching logs from Loki: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error logs from Loki.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        # Enhance query with error filter
        error_query = '{job="varlogs"} |~ "(?i)(error|critical|exception|failed)"'

        if filters and 'query' in filters:
            error_query = f"{filters['query']} |~ \"(?i)(error|critical|exception|failed)\""

        if filters:
            filters = filters.copy()
        else:
            filters = {}

        filters['query'] = error_query
        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from Prometheus via Grafana.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            List of PerformanceMetric objects
        """
        metrics = []

        # Default metrics if none specified
        if not metric_names:
            metric_names = [
                'up',
                'node_cpu_seconds_total',
                'node_memory_MemAvailable_bytes',
                'http_requests_total'
            ]

        for metric_name in metric_names:
            url = f"{self.prometheus_url}/api/v1/query_range"

            params = {
                'query': metric_name,
                'start': start_time.timestamp(),
                'end': end_time.timestamp(),
                'step': '60s'
            }

            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                data = response.json()

                for result in data.get('data', {}).get('result', []):
                    metric_labels = result.get('metric', {})
                    values = result.get('values', [])

                    for timestamp, value in values:
                        try:
                            metric = PerformanceMetric(
                                metric_name=metric_name,
                                value=float(value),
                                unit='unknown',
                                timestamp=datetime.fromtimestamp(timestamp),
                                dimensions=metric_labels
                            )
                            metrics.append(metric)
                        except (ValueError, TypeError):
                            continue

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching metric {metric_name}: {e}")

        logger.info(f"Fetched {len(metrics)} metrics from Prometheus via Grafana")
        return metrics

    def get_dashboards(self) -> List[Dict[str, Any]]:
        """
        Get list of Grafana dashboards.

        Returns:
            List of dashboard dictionaries
        """
        url = f"{self.grafana_url}/api/search"

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            dashboards = response.json()
            logger.info(f"Retrieved {len(dashboards)} dashboards from Grafana")
            return dashboards

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Grafana dashboards: {e}")
            return []

    def _infer_level(self, message: str) -> str:
        """Infer log level from message content."""
        msg_lower = message.lower()

        if any(word in msg_lower for word in ['critical', 'fatal']):
            return 'CRITICAL'
        elif any(word in msg_lower for word in ['error', 'exception']):
            return 'ERROR'
        elif any(word in msg_lower for word in ['warning', 'warn']):
            return 'WARNING'
        elif any(word in msg_lower for word in ['debug', 'trace']):
            return 'DEBUG'
        else:
            return 'INFO'

    def test_connection(self) -> bool:
        """Test connection to Grafana."""
        try:
            url = f"{self.grafana_url}/api/health"
            response = self.session.get(
                url,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            logger.info("Grafana connection test: SUCCESS")
            return True
        except Exception as e:
            logger.error(f"Grafana connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
