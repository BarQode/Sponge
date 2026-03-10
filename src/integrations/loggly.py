"""
Loggly Integration for Log Retrieval.

Connects to Loggly REST API for log search and retrieval.
Supports JSON-based search with facets and statistical queries.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class LogglyIntegration(BaseIntegration):
    """
    Integration with Loggly for log retrieval and search.

    Features:
    - Full-text log search
    - Faceted search
    - Field extraction
    - Connection pooling
    - Automatic retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Loggly integration.

        Args:
            config: Configuration dict with:
                - account_name: Loggly account/subdomain name
                - api_token: Loggly API token
                - api_url: API URL (default: 'https://[account].loggly.com/apiv2')
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.account_name = config.get('account_name', '')
        self.api_token = config.get('api_token', '')
        self.api_url = config.get('api_url',
                                  f"https://{self.account_name}.loggly.com/apiv2")
        self.timeout = config.get('timeout', 30)

        # Create session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Loggly integration initialized for account: {self.account_name}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Loggly.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (query, tag, field filters)

        Returns:
            List of LogEntry objects
        """
        # Build search query
        query = filters.get('query', '*') if filters else '*'

        # Add tags if specified
        if filters and 'tags' in filters:
            tags = filters['tags']
            if isinstance(tags, list):
                query = f"tag:{','.join(tags)} {query}"
            else:
                query = f"tag:{tags} {query}"

        # Step 1: Create search
        search_url = f"{self.api_url}/search"
        params = {
            'q': query,
            'from': start_time.isoformat(),
            'until': end_time.isoformat(),
            'size': filters.get('size', 1000) if filters else 1000
        }

        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        logs = []

        try:
            # Execute search
            response = self.session.get(
                search_url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Get RSID (search ID) for fetching events
            rsid = data.get('rsid', {}).get('id')

            if rsid:
                # Step 2: Fetch events using RSID
                events_url = f"{self.api_url}/events"
                events_params = {'rsid': rsid}

                events_response = self.session.get(
                    events_url,
                    params=events_params,
                    headers=headers,
                    timeout=self.timeout
                )
                events_response.raise_for_status()
                events_data = events_response.json()

                for event in events_data.get('events', []):
                    event_data = event.get('event', {})

                    log = LogEntry(
                        timestamp=datetime.fromisoformat(
                            event_data.get('timestamp', '').replace('Z', '+00:00')
                        ),
                        message=event_data.get('message', event_data.get('json', {}).get('message', '')),
                        level=self._infer_level(event_data),
                        source='loggly',
                        metadata={
                            'tags': event.get('tags', []),
                            'logtypes': event.get('logtypes', []),
                            **event_data.get('json', {})
                        }
                    )
                    logs.append(log)

            logger.info(f"Fetched {len(logs)} logs from Loggly")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Loggly logs: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error logs from Loggly.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        if filters:
            filters = filters.copy()
            error_query = '(error OR ERROR OR exception OR critical OR CRITICAL OR failed OR FAILED)'
            if 'query' in filters:
                filters['query'] = f"{filters['query']} AND {error_query}"
            else:
                filters['query'] = error_query
        else:
            filters = {'query': '(error OR ERROR OR exception OR critical OR CRITICAL OR failed)'}

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Loggly is log-focused; metrics can be derived from logs but not natively stored.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            Empty list (use field-based statistics for metrics)
        """
        logger.info("Loggly doesn't natively support metrics - use field statistics or log-based metrics")
        return []

    def _infer_level(self, event_data: Dict[str, Any]) -> str:
        """Infer log level from event data."""
        # Check for explicit level field
        json_data = event_data.get('json', {})
        level = json_data.get('level', json_data.get('severity', json_data.get('loglevel', ''))).upper()

        if level in ['CRITICAL', 'FATAL', 'EMERGENCY']:
            return 'CRITICAL'
        elif level in ['ERROR']:
            return 'ERROR'
        elif level in ['WARNING', 'WARN']:
            return 'WARNING'
        elif level in ['INFO', 'INFORMATION']:
            return 'INFO'
        elif level in ['DEBUG', 'TRACE']:
            return 'DEBUG'

        # Fallback: infer from message
        message = event_data.get('message', '').lower()
        if any(word in message for word in ['critical', 'fatal']):
            return 'CRITICAL'
        elif any(word in message for word in ['error', 'exception']):
            return 'ERROR'
        elif any(word in message for word in ['warning', 'warn']):
            return 'WARNING'

        return 'INFO'

    def test_connection(self) -> bool:
        """Test connection to Loggly API."""
        try:
            url = f"{self.api_url}/customer"
            headers = {'Authorization': f'Bearer {self.api_token}'}
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            logger.info("Loggly connection test: SUCCESS")
            return True
        except Exception as e:
            logger.error(f"Loggly connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
