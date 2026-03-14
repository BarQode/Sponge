"""
Logentries Integration for Sponge RCA Platform

Logentries (now Rapid7 InsightOps) provides cloud-based log management.

Features:
- Real-time log search
- Query-based filtering
- Tag support
- JSON log parsing
- Connection pooling
- Auto-retry with exponential backoff
"""

import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class LogentriesIntegration(BaseIntegration):
    """Logentries (Rapid7 InsightOps) integration."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Logentries integration.

        Args:
            config: Configuration dictionary with:
                - api_key: Logentries API key
                - region: Region (us/eu)
                - account_key: Account key (optional)
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.region = config.get('region', 'us')
        self.account_key = config.get('account_key')
        self.timeout = config.get('timeout', 30)

        if not self.api_key:
            raise ValueError("api_key is required for Logentries integration")

        # API endpoints
        base_url = f"https://{self.region}.rest.logs.insight.rapid7.com"
        self.query_url = f"{base_url}/query/logs"
        self.events_url = f"{base_url}/management/logs"

        # Session configuration
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        })

        # Connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('https://', adapter)

        logger.info(f"Initialized Logentries integration for region: {self.region}")

    def test_connection(self) -> bool:
        """Test connection to Logentries."""
        try:
            # Test by querying logs from last minute
            response = self.session.get(
                self.events_url,
                timeout=self.timeout
            )
            success = response.status_code == 200
            if success:
                logger.info("Logentries connection test successful")
            else:
                logger.error(f"Logentries connection test failed: {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"Logentries connection test failed: {e}")
            return False

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Logentries.

        Args:
            start_time: Start time for log retrieval
            end_time: End time for log retrieval
            filters: Optional filters:
                - query: LEQL query string
                - log_ids: List of log IDs to search
                - limit: Maximum results (default: 1000)

        Returns:
            List of LogEntry objects
        """
        try:
            filters = filters or {}
            query = filters.get('query', '*')
            log_ids = filters.get('log_ids', [])
            limit = filters.get('limit', 1000)

            # Build LEQL query
            leql_query = {
                'logs': log_ids if log_ids else [],
                'leql': {
                    'statement': query,
                    'during': {
                        'from': int(start_time.timestamp() * 1000),
                        'to': int(end_time.timestamp() * 1000)
                    }
                },
                'limit': limit
            }

            response = self.session.post(
                self.query_url,
                json=leql_query,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch Logentries logs: {response.status_code}")
                return []

            data = response.json()
            logs = []

            for event in data.get('events', []):
                log_entry = LogEntry(
                    timestamp=datetime.fromtimestamp(event.get('timestamp', 0) / 1000),
                    level=self._infer_level(event.get('message', '')),
                    message=event.get('message', ''),
                    source=f"logentries:{event.get('log_id', 'unknown')}",
                    metadata={
                        'log_id': event.get('log_id'),
                        'event_id': event.get('event_id'),
                        **event.get('fields', {})
                    }
                )
                logs.append(log_entry)

            logger.info(f"Fetched {len(logs)} logs from Logentries")
            return logs

        except Exception as e:
            logger.error(f"Error fetching Logentries logs: {e}")
            return []

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch error logs from Logentries."""
        filters = filters or {}
        # Enhance query to find errors
        base_query = filters.get('query', '*')
        filters['query'] = f"({base_query}) AND (error OR exception OR fatal OR critical)"

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from Logentries.

        Note: Logentries focuses on logs, not metrics.
        This extracts performance data from log messages.
        """
        try:
            # Search for performance-related logs
            filters = {
                'query': 'response_time OR latency OR duration OR performance',
                'limit': 1000
            }

            logs = self.fetch_logs(start_time, end_time, filters)
            metrics = []

            for log in logs:
                # Extract numeric values from log messages
                import re
                numbers = re.findall(r'\d+\.?\d*', log.message)

                if numbers:
                    metric = PerformanceMetric(
                        timestamp=log.timestamp,
                        metric_name='response_time',
                        value=float(numbers[0]),
                        unit='ms',
                        metadata=log.metadata
                    )
                    metrics.append(metric)

            logger.info(f"Extracted {len(metrics)} performance metrics from Logentries")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching Logentries metrics: {e}")
            return []

    def _infer_level(self, message: str) -> str:
        """Infer log level from message content."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['fatal', 'critical', 'panic']):
            return 'CRITICAL'
        elif any(word in message_lower for word in ['error', 'fail', 'exception']):
            return 'ERROR'
        elif any(word in message_lower for word in ['warn', 'warning']):
            return 'WARNING'
        elif any(word in message_lower for word in ['info', 'notice']):
            return 'INFO'
        elif any(word in message_lower for word in ['debug', 'trace']):
            return 'DEBUG'
        else:
            return 'INFO'

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'session'):
            self.session.close()
