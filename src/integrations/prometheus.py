"""
Prometheus Integration for Log and Metric Retrieval.

Queries Prometheus for metrics, alerts, and log-based metrics.
Supports PromQL queries for advanced metric analysis.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class PrometheusIntegration(BaseIntegration):
    """
    Integration with Prometheus for metrics and alert retrieval.

    Features:
    - PromQL query execution
    - Metric retrieval with time ranges
    - Alert status monitoring
    - Connection pooling for performance
    - Automatic retry logic with exponential backoff
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Prometheus integration.

        Args:
            config: Configuration dict with:
                - prometheus_url: Base URL of Prometheus server
                - timeout: Request timeout in seconds (default: 30)
                - verify_ssl: Verify SSL certificates (default: True)
        """
        super().__init__(config)
        self.base_url = config.get('prometheus_url', 'http://localhost:9090')
        self.timeout = config.get('timeout', 30)
        self.verify_ssl = config.get('verify_ssl', True)

        # Create session with connection pooling and retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Prometheus integration initialized: {self.base_url}")

    def _execute_query(self, query: str, time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Execute a PromQL query.

        Args:
            query: PromQL query string
            time: Optional timestamp for point-in-time query

        Returns:
            Query result dictionary
        """
        url = f"{self.base_url}/api/v1/query"
        params = {'query': query}

        if time:
            params['time'] = time.timestamp()

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'success':
                logger.error(f"Query failed: {data.get('error', 'Unknown error')}")
                return {'data': {'result': []}}

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus query error: {e}")
            return {'data': {'result': []}}

    def _execute_range_query(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        step: str = '15s'
    ) -> Dict[str, Any]:
        """
        Execute a PromQL range query.

        Args:
            query: PromQL query string
            start_time: Start of time range
            end_time: End of time range
            step: Query resolution (e.g., '15s', '1m', '5m')

        Returns:
            Range query result dictionary
        """
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            'query': query,
            'start': start_time.timestamp(),
            'end': end_time.timestamp(),
            'step': step
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

            if data.get('status') != 'success':
                logger.error(f"Range query failed: {data.get('error', 'Unknown error')}")
                return {'data': {'result': []}}

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus range query error: {e}")
            return {'data': {'result': []}}

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch log-based metrics from Prometheus.

        Prometheus doesn't store logs directly, but can track log-based metrics.
        This method queries for alert states and metric anomalies.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (log_level, service_name, etc.)

        Returns:
            List of LogEntry objects derived from alerts and metrics
        """
        logs = []

        # Query for active alerts (treated as log entries)
        try:
            alerts_url = f"{self.base_url}/api/v1/alerts"
            response = self.session.get(
                alerts_url,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'success':
                for alert in data.get('data', {}).get('alerts', []):
                    alert_state = alert.get('state', 'unknown')
                    alert_name = alert.get('labels', {}).get('alertname', 'Unknown')
                    severity = alert.get('labels', {}).get('severity', 'warning')

                    # Convert alert to log entry
                    log = LogEntry(
                        timestamp=datetime.utcnow(),
                        message=f"Alert: {alert_name} - {alert.get('annotations', {}).get('summary', '')}",
                        level=severity.upper() if severity in ['critical', 'error'] else 'WARNING',
                        source='prometheus_alerts',
                        metadata={
                            'alert_name': alert_name,
                            'state': alert_state,
                            'labels': alert.get('labels', {}),
                            'annotations': alert.get('annotations', {})
                        }
                    )
                    logs.append(log)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Prometheus alerts: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error-level alerts from Prometheus.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error-level LogEntry objects
        """
        all_logs = self.fetch_logs(start_time, end_time, filters)
        return [log for log in all_logs if log.level in ['ERROR', 'CRITICAL']]

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from Prometheus.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query (None = common metrics)

        Returns:
            List of PerformanceMetric objects
        """
        metrics = []

        # Default metrics if none specified
        if not metric_names:
            metric_names = [
                'node_cpu_seconds_total',
                'node_memory_MemAvailable_bytes',
                'node_memory_MemTotal_bytes',
                'http_request_duration_seconds',
                'http_requests_total',
                'up'  # Service availability
            ]

        for metric_name in metric_names:
            query_result = self._execute_range_query(
                metric_name,
                start_time,
                end_time,
                step='1m'
            )

            for result in query_result.get('data', {}).get('result', []):
                metric_labels = result.get('metric', {})
                values = result.get('values', [])

                for timestamp, value in values:
                    try:
                        metric = PerformanceMetric(
                            metric_name=metric_name,
                            value=float(value),
                            unit=self._infer_unit(metric_name),
                            timestamp=datetime.fromtimestamp(timestamp),
                            dimensions=metric_labels
                        )
                        metrics.append(metric)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing metric value: {e}")
                        continue

        return metrics

    def _infer_unit(self, metric_name: str) -> str:
        """Infer metric unit from metric name."""
        if 'bytes' in metric_name.lower():
            return 'bytes'
        elif 'seconds' in metric_name.lower():
            return 'seconds'
        elif 'percent' in metric_name.lower() or 'usage' in metric_name.lower():
            return 'percent'
        elif 'total' in metric_name.lower() or 'count' in metric_name.lower():
            return 'count'
        else:
            return 'unknown'

    def query_metric(self, promql: str, time: Optional[datetime] = None) -> List[PerformanceMetric]:
        """
        Execute a custom PromQL query and return metrics.

        Args:
            promql: PromQL query string
            time: Optional point-in-time for query

        Returns:
            List of PerformanceMetric objects
        """
        metrics = []
        query_result = self._execute_query(promql, time)

        for result in query_result.get('data', {}).get('result', []):
            metric_labels = result.get('metric', {})
            value_data = result.get('value', [])

            if len(value_data) >= 2:
                timestamp, value = value_data[0], value_data[1]

                try:
                    metric = PerformanceMetric(
                        metric_name=promql,
                        value=float(value),
                        unit='custom',
                        timestamp=datetime.fromtimestamp(timestamp),
                        dimensions=metric_labels
                    )
                    metrics.append(metric)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing custom query result: {e}")

        return metrics

    def test_connection(self) -> bool:
        """Test connection to Prometheus server."""
        try:
            url = f"{self.base_url}/api/v1/query"
            response = self.session.get(
                url,
                params={'query': 'up'},
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'success':
                logger.info("Prometheus connection test: SUCCESS")
                return True
            else:
                logger.error(f"Prometheus connection test FAILED: {data.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Prometheus connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
