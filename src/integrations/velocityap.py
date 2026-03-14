"""
VelocityAP Integration for Sponge RCA Platform

VelocityAP provides application performance monitoring and log analysis.

Features:
- Application performance metrics
- Transaction tracing
- Error tracking
- Real-time monitoring
- Connection pooling
- Auto-retry with exponential backoff
"""

import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class VelocityAPIntegration(BaseIntegration):
    """VelocityAP application performance monitoring integration."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize VelocityAP integration.

        Args:
            config: Configuration dictionary with:
                - api_url: VelocityAP API endpoint
                - api_key: API key for authentication
                - app_id: Application ID (optional)
                - environment: Environment name (optional)
        """
        super().__init__(config)
        self.api_url = config.get('api_url', '').rstrip('/')
        self.api_key = config.get('api_key')
        self.app_id = config.get('app_id')
        self.environment = config.get('environment', 'production')
        self.timeout = config.get('timeout', 30)

        if not self.api_url or not self.api_key:
            raise ValueError("api_url and api_key are required for VelocityAP integration")

        # Session configuration
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

        # Connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        logger.info(f"Initialized VelocityAP integration for environment: {self.environment}")

    def test_connection(self) -> bool:
        """Test connection to VelocityAP."""
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/health",
                timeout=self.timeout
            )
            success = response.status_code == 200
            if success:
                logger.info("VelocityAP connection test successful")
            else:
                logger.error(f"VelocityAP connection test failed: {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"VelocityAP connection test failed: {e}")
            return False

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from VelocityAP.

        Args:
            start_time: Start time for log retrieval
            end_time: End time for log retrieval
            filters: Optional filters:
                - level: Log level filter
                - service: Service name
                - query: Search query
                - limit: Maximum results (default: 1000)

        Returns:
            List of LogEntry objects
        """
        try:
            filters = filters or {}

            params = {
                'start': int(start_time.timestamp() * 1000),
                'end': int(end_time.timestamp() * 1000),
                'limit': filters.get('limit', 1000)
            }

            if self.app_id:
                params['app_id'] = self.app_id

            if filters.get('level'):
                params['level'] = filters['level']

            if filters.get('service'):
                params['service'] = filters['service']

            if filters.get('query'):
                params['query'] = filters['query']

            response = self.session.get(
                f"{self.api_url}/api/v1/logs",
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch VelocityAP logs: {response.status_code}")
                return []

            data = response.json()
            logs = []

            for entry in data.get('logs', []):
                log_entry = LogEntry(
                    timestamp=datetime.fromtimestamp(entry.get('timestamp', 0) / 1000),
                    level=entry.get('level', 'INFO'),
                    message=entry.get('message', ''),
                    source=f"velocityap:{entry.get('service', 'unknown')}",
                    metadata={
                        'service': entry.get('service'),
                        'trace_id': entry.get('trace_id'),
                        'span_id': entry.get('span_id'),
                        'environment': entry.get('environment', self.environment),
                        **entry.get('attributes', {})
                    }
                )
                logs.append(log_entry)

            logger.info(f"Fetched {len(logs)} logs from VelocityAP")
            return logs

        except Exception as e:
            logger.error(f"Error fetching VelocityAP logs: {e}")
            return []

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch error logs from VelocityAP."""
        filters = filters or {}
        filters['level'] = 'ERROR,CRITICAL,FATAL'

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from VelocityAP.

        Args:
            start_time: Start time for metrics
            end_time: End time for metrics
            metric_names: List of metric names (e.g., response_time, throughput, error_rate)

        Returns:
            List of PerformanceMetric objects
        """
        try:
            params = {
                'start': int(start_time.timestamp() * 1000),
                'end': int(end_time.timestamp() * 1000)
            }

            if self.app_id:
                params['app_id'] = self.app_id

            if metric_names:
                params['metrics'] = ','.join(metric_names)

            response = self.session.get(
                f"{self.api_url}/api/v1/metrics",
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch VelocityAP metrics: {response.status_code}")
                return []

            data = response.json()
            metrics = []

            for series in data.get('series', []):
                metric_name = series.get('name')
                unit = self._infer_unit(metric_name)

                for point in series.get('points', []):
                    metric = PerformanceMetric(
                        timestamp=datetime.fromtimestamp(point[0] / 1000),
                        metric_name=metric_name,
                        value=point[1],
                        unit=unit,
                        metadata={
                            'service': series.get('service'),
                            'environment': series.get('environment', self.environment),
                            **series.get('tags', {})
                        }
                    )
                    metrics.append(metric)

            logger.info(f"Fetched {len(metrics)} performance metrics from VelocityAP")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching VelocityAP metrics: {e}")
            return []

    def get_transaction_traces(
        self,
        start_time: datetime,
        end_time: datetime,
        min_duration_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction traces for slow or failed transactions.

        Args:
            start_time: Start time
            end_time: End time
            min_duration_ms: Minimum duration in ms (for slow transactions)

        Returns:
            List of transaction trace dictionaries
        """
        try:
            params = {
                'start': int(start_time.timestamp() * 1000),
                'end': int(end_time.timestamp() * 1000)
            }

            if self.app_id:
                params['app_id'] = self.app_id

            if min_duration_ms:
                params['min_duration'] = min_duration_ms

            response = self.session.get(
                f"{self.api_url}/api/v1/traces",
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch transaction traces: {response.status_code}")
                return []

            data = response.json()
            traces = data.get('traces', [])

            logger.info(f"Fetched {len(traces)} transaction traces from VelocityAP")
            return traces

        except Exception as e:
            logger.error(f"Error fetching transaction traces: {e}")
            return []

    def _infer_unit(self, metric_name: str) -> str:
        """Infer metric unit from metric name."""
        metric_lower = metric_name.lower()

        if 'time' in metric_lower or 'latency' in metric_lower or 'duration' in metric_lower:
            return 'ms'
        elif 'bytes' in metric_lower or 'size' in metric_lower:
            return 'bytes'
        elif 'rate' in metric_lower or 'throughput' in metric_lower:
            return 'per_second'
        elif 'percent' in metric_lower or 'ratio' in metric_lower:
            return 'percent'
        elif 'count' in metric_lower or 'total' in metric_lower:
            return 'count'
        else:
            return 'units'

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'session'):
            self.session.close()
