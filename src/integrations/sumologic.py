"""
Sumo Logic Integration for Log and Metric Retrieval.

Queries Sumo Logic Search API for logs, metrics, and alerts.
Supports complex search queries and metric queries.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter, Retry
import time
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class SumoLogicIntegration(BaseIntegration):
    """
    Integration with Sumo Logic for log and metric retrieval.

    Features:
    - Log search with Sumo Logic query language
    - Metric queries
    - Alert retrieval
    - Async search with polling
    - Connection pooling and retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Sumo Logic integration.

        Args:
            config: Configuration dict with:
                - access_id: Sumo Logic access ID
                - access_key: Sumo Logic access key
                - api_endpoint: API endpoint URL (e.g., 'https://api.sumologic.com/api')
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.access_id = config.get('access_id', '')
        self.access_key = config.get('access_key', '')
        self.api_endpoint = config.get('api_endpoint', 'https://api.sumologic.com/api')
        self.timeout = config.get('timeout', 30)

        # Create session with auth and retry logic
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.access_id, self.access_key)
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Sumo Logic integration initialized: {self.api_endpoint}")

    def _create_search_job(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        timezone: str = 'UTC'
    ) -> Optional[str]:
        """
        Create an async search job in Sumo Logic.

        Args:
            query: Sumo Logic search query
            start_time: Start time for search
            end_time: End time for search
            timezone: Timezone for search

        Returns:
            Search job ID or None if failed
        """
        url = f"{self.api_endpoint}/v1/search/jobs"

        payload = {
            'query': query,
            'from': int(start_time.timestamp() * 1000),  # milliseconds
            'to': int(end_time.timestamp() * 1000),
            'timeZone': timezone
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            job_id = data.get('id')
            logger.info(f"Created Sumo Logic search job: {job_id}")
            return job_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Sumo Logic search job: {e}")
            return None

    def _poll_search_job(self, job_id: str, max_wait: int = 120) -> Optional[Dict[str, Any]]:
        """
        Poll search job until complete or timeout.

        Args:
            job_id: Search job ID
            max_wait: Maximum wait time in seconds

        Returns:
            Search results or None if timeout/error
        """
        url = f"{self.api_endpoint}/v1/search/jobs/{job_id}"
        start = time.time()

        while time.time() - start < max_wait:
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                state = data.get('state', '')

                if state == 'DONE GATHERING RESULTS':
                    logger.info(f"Search job {job_id} completed")
                    return self._fetch_search_results(job_id)
                elif state in ['CANCELLED', 'FAILED']:
                    logger.error(f"Search job {job_id} failed with state: {state}")
                    return None

                # Wait before polling again
                time.sleep(2)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error polling search job {job_id}: {e}")
                return None

        logger.warning(f"Search job {job_id} timed out after {max_wait}s")
        return None

    def _fetch_search_results(self, job_id: str, limit: int = 10000) -> Optional[Dict[str, Any]]:
        """
        Fetch results from completed search job.

        Args:
            job_id: Search job ID
            limit: Maximum number of results

        Returns:
            Search results dictionary
        """
        url = f"{self.api_endpoint}/v1/search/jobs/{job_id}/messages"
        params = {'offset': 0, 'limit': limit}

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching search results for job {job_id}: {e}")
            return None

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Sumo Logic.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (query, source_category, etc.)

        Returns:
            List of LogEntry objects
        """
        # Build search query
        base_query = filters.get('query', '*') if filters else '*'

        if filters:
            if 'source_category' in filters:
                base_query += f" _sourceCategory={filters['source_category']}"
            if 'source_name' in filters:
                base_query += f" _sourceName={filters['source_name']}"

        # Create and execute search job
        job_id = self._create_search_job(base_query, start_time, end_time)
        if not job_id:
            return []

        results = self._poll_search_job(job_id)
        if not results:
            return []

        # Convert to LogEntry objects
        logs = []
        for message in results.get('messages', []):
            msg_map = message.get('map', {})

            log = LogEntry(
                timestamp=datetime.fromtimestamp(msg_map.get('_messagetime', 0) / 1000),
                message=msg_map.get('_raw', ''),
                level=self._infer_level(msg_map.get('_raw', '')),
                source='sumologic',
                metadata={
                    'source_category': msg_map.get('_sourceCategory'),
                    'source_name': msg_map.get('_sourceName'),
                    'source_host': msg_map.get('_sourceHost'),
                    'collector': msg_map.get('_collector')
                }
            )
            logs.append(log)

        logger.info(f"Fetched {len(logs)} logs from Sumo Logic")
        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error logs from Sumo Logic.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        # Enhance query to filter errors
        error_query = '* (error OR ERROR OR critical OR CRITICAL OR exception OR Exception OR failed OR FAILED)'

        if filters:
            filters = filters.copy()
            if 'query' in filters:
                filters['query'] = f"{filters['query']} AND ({error_query})"
            else:
                filters['query'] = error_query
        else:
            filters = {'query': error_query}

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from Sumo Logic Metrics.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            List of PerformanceMetric objects
        """
        # Sumo Logic Metrics API
        metrics = []

        if not metric_names:
            # Default metric queries
            metric_names = ['cpu.usage', 'memory.usage', 'disk.usage']

        for metric_name in metric_names:
            query = f"metric={metric_name}"
            job_id = self._create_search_job(query, start_time, end_time)

            if job_id:
                results = self._poll_search_job(job_id)
                if results:
                    for data_point in results.get('records', []):
                        try:
                            metric = PerformanceMetric(
                                metric_name=metric_name,
                                value=float(data_point.get('value', 0)),
                                unit=data_point.get('unit', 'unknown'),
                                timestamp=datetime.fromtimestamp(data_point.get('timestamp', 0) / 1000),
                                dimensions=data_point.get('dimensions', {})
                            )
                            metrics.append(metric)
                        except (ValueError, TypeError):
                            continue

        return metrics

    def _infer_level(self, message: str) -> str:
        """Infer log level from message content."""
        msg_lower = message.lower()

        if any(word in msg_lower for word in ['critical', 'fatal', 'emergency']):
            return 'CRITICAL'
        elif any(word in msg_lower for word in ['error', 'exception', 'failed']):
            return 'ERROR'
        elif any(word in msg_lower for word in ['warning', 'warn']):
            return 'WARNING'
        elif any(word in msg_lower for word in ['info', 'information']):
            return 'INFO'
        elif any(word in msg_lower for word in ['debug', 'trace']):
            return 'DEBUG'
        else:
            return 'INFO'

    def test_connection(self) -> bool:
        """Test connection to Sumo Logic API."""
        try:
            url = f"{self.api_endpoint}/v1/collectors"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            logger.info("Sumo Logic connection test: SUCCESS")
            return True
        except Exception as e:
            logger.error(f"Sumo Logic connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
