"""
Retrace (Stackify) Integration for Log and APM Data Retrieval.

Connects to Stackify Retrace API for application performance monitoring,
error tracking, and log management.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class RetraceIntegration(BaseIntegration):
    """
    Integration with Stackify Retrace for APM and log retrieval.

    Features:
    - Application performance monitoring
    - Error and exception tracking
    - Log aggregation and search
    - Transaction tracing
    - Connection pooling with retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Retrace integration.

        Args:
            config: Configuration dict with:
                - api_key: Stackify API key
                - api_url: API endpoint (default: 'https://api.stackify.com')
                - app_id: Application ID
                - environment: Environment name (e.g., 'Production', 'Staging')
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_url = config.get('api_url', 'https://api.stackify.com')
        self.app_id = config.get('app_id', '')
        self.environment = config.get('environment', 'Production')
        self.timeout = config.get('timeout', 30)

        # Create session with auth header
        self.session = requests.Session()
        self.session.headers.update({
            'X-Stackify-Key': self.api_key,
            'Content-Type': 'application/json'
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

        logger.info(f"Retrace integration initialized for app: {self.app_id}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Retrace.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (level, logger_name, query)

        Returns:
            List of LogEntry objects
        """
        url = f"{self.api_url}/Logs/Search"

        params = {
            'AppID': self.app_id,
            'Env': self.environment,
            'StartDate': start_time.isoformat(),
            'EndDate': end_time.isoformat()
        }

        if filters:
            if 'level' in filters:
                params['Level'] = filters['level']
            if 'logger_name' in filters:
                params['LoggerName'] = filters['logger_name']
            if 'query' in filters:
                params['Query'] = filters['query']

        logs = []

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            for log_entry in data.get('Logs', []):
                log = LogEntry(
                    timestamp=datetime.fromisoformat(
                        log_entry.get('OccurredUtc', '').replace('Z', '+00:00')
                    ),
                    message=log_entry.get('Message', ''),
                    level=log_entry.get('Level', 'INFO').upper(),
                    source='retrace',
                    metadata={
                        'logger_name': log_entry.get('LoggerName'),
                        'exception': log_entry.get('Exception'),
                        'thread_id': log_entry.get('ThreadID'),
                        'server_name': log_entry.get('ServerName'),
                        'app_name': log_entry.get('AppName'),
                        'transaction_id': log_entry.get('TransactionID'),
                        'request_id': log_entry.get('RequestID')
                    }
                )
                logs.append(log)

            logger.info(f"Fetched {len(logs)} logs from Retrace")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Retrace logs: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error and exception logs from Retrace.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        url = f"{self.api_url}/Errors/Search"

        params = {
            'AppID': self.app_id,
            'Env': self.environment,
            'StartDate': start_time.isoformat(),
            'EndDate': end_time.isoformat()
        }

        if filters and 'query' in filters:
            params['Query'] = filters['query']

        errors = []

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            for error_entry in data.get('Errors', []):
                error = LogEntry(
                    timestamp=datetime.fromisoformat(
                        error_entry.get('OccurredUtc', '').replace('Z', '+00:00')
                    ),
                    message=error_entry.get('ErrorMessage', ''),
                    level='ERROR',
                    source='retrace',
                    metadata={
                        'error_type': error_entry.get('ErrorType'),
                        'stack_trace': error_entry.get('StackTrace'),
                        'inner_exception': error_entry.get('InnerException'),
                        'server_name': error_entry.get('ServerName'),
                        'app_name': error_entry.get('AppName'),
                        'count': error_entry.get('Count'),
                        'transaction_id': error_entry.get('TransactionID')
                    }
                )
                errors.append(error)

            logger.info(f"Fetched {len(errors)} errors from Retrace")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Retrace errors: {e}")

        return errors

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch APM performance metrics from Retrace.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            List of PerformanceMetric objects
        """
        url = f"{self.api_url}/Metrics/App/{self.app_id}"

        params = {
            'Env': self.environment,
            'StartDate': start_time.isoformat(),
            'EndDate': end_time.isoformat()
        }

        metrics = []

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Extract common performance metrics
            for metric_data in data.get('Metrics', []):
                metric = PerformanceMetric(
                    metric_name=metric_data.get('Name', 'unknown'),
                    value=float(metric_data.get('Value', 0)),
                    unit=metric_data.get('Unit', 'unknown'),
                    timestamp=datetime.fromisoformat(
                        metric_data.get('Timestamp', '').replace('Z', '+00:00')
                    ),
                    dimensions={
                        'app_id': self.app_id,
                        'environment': self.environment,
                        'server': metric_data.get('ServerName', '')
                    }
                )
                metrics.append(metric)

            logger.info(f"Fetched {len(metrics)} performance metrics from Retrace")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Retrace metrics: {e}")

        return metrics

    def get_transaction_traces(
        self,
        start_time: datetime,
        end_time: datetime,
        min_duration_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get transaction traces for slow transactions.

        Args:
            start_time: Start of time range
            end_time: End of time range
            min_duration_ms: Minimum transaction duration in milliseconds

        Returns:
            List of transaction trace dictionaries
        """
        url = f"{self.api_url}/Transactions/Traces"

        params = {
            'AppID': self.app_id,
            'Env': self.environment,
            'StartDate': start_time.isoformat(),
            'EndDate': end_time.isoformat(),
            'MinDuration': min_duration_ms
        }

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            traces = data.get('Traces', [])
            logger.info(f"Retrieved {len(traces)} transaction traces from Retrace")
            return traces

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transaction traces: {e}")
            return []

    def test_connection(self) -> bool:
        """Test connection to Retrace API."""
        try:
            url = f"{self.api_url}/Apps/{self.app_id}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            logger.info("Retrace connection test: SUCCESS")
            return True
        except Exception as e:
            logger.error(f"Retrace connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
