"""
Fluentd Integration for Log Retrieval.

Connects to Fluentd via HTTP output plugin or forward protocol.
Supports structured log ingestion and query.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
import json
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class FluentdIntegration(BaseIntegration):
    """
    Integration with Fluentd for log retrieval.

    Features:
    - HTTP endpoint querying
    - Structured log parsing
    - Tag-based filtering
    - Connection pooling
    - Automatic retry logic

    Note: Fluentd doesn't have a native query API, so this integration
    works with Fluentd HTTP output or storage backends (Elasticsearch, etc.)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Fluentd integration.

        Args:
            config: Configuration dict with:
                - http_endpoint: Fluentd HTTP endpoint URL
                - storage_backend: Storage backend type ('elasticsearch', 'mongodb', etc.)
                - backend_config: Config for storage backend
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.http_endpoint = config.get('http_endpoint', 'http://localhost:9880')
        self.storage_backend = config.get('storage_backend', 'http')
        self.backend_config = config.get('backend_config', {})
        self.timeout = config.get('timeout', 30)

        # Create session
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

        # Initialize storage backend if configured
        self.backend_client = None
        if self.storage_backend == 'elasticsearch':
            self._init_elasticsearch_backend()

        logger.info(f"Fluentd integration initialized: {self.http_endpoint}")

    def _init_elasticsearch_backend(self):
        """Initialize Elasticsearch backend for querying Fluentd logs."""
        try:
            from elasticsearch import Elasticsearch

            es_hosts = self.backend_config.get('hosts', ['http://localhost:9200'])
            self.backend_client = Elasticsearch(hosts=es_hosts)
            logger.info("Initialized Elasticsearch backend for Fluentd")

        except ImportError:
            logger.warning("Elasticsearch library not installed - install with: pip install elasticsearch")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch backend: {e}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Fluentd storage backend.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (tag, match pattern)

        Returns:
            List of LogEntry objects
        """
        if self.storage_backend == 'elasticsearch' and self.backend_client:
            return self._fetch_from_elasticsearch(start_time, end_time, filters)
        else:
            logger.warning("No queryable storage backend configured for Fluentd")
            return []

    def _fetch_from_elasticsearch(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch logs from Elasticsearch backend."""
        logs = []

        try:
            # Build Elasticsearch query
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "range": {
                                    "@timestamp": {
                                        "gte": start_time.isoformat(),
                                        "lte": end_time.isoformat()
                                    }
                                }
                            }
                        ]
                    }
                }
            }

            # Add tag filter if specified
            if filters and 'tag' in filters:
                query["query"]["bool"]["must"].append({
                    "match": {"tag": filters['tag']}
                })

            # Add custom query if specified
            if filters and 'query' in filters:
                query["query"]["bool"]["must"].append({
                    "query_string": {"query": filters['query']}
                })

            index_pattern = filters.get('index', 'fluentd-*') if filters else 'fluentd-*'

            # Execute search
            response = self.backend_client.search(
                index=index_pattern,
                body=query,
                size=filters.get('size', 1000) if filters else 1000
            )

            for hit in response['hits']['hits']:
                source = hit['_source']

                log = LogEntry(
                    timestamp=datetime.fromisoformat(
                        source.get('@timestamp', '').replace('Z', '+00:00')
                    ),
                    message=source.get('message', source.get('log', '')),
                    level=source.get('level', 'INFO').upper(),
                    source='fluentd',
                    metadata={
                        'tag': source.get('tag'),
                        'container_name': source.get('container_name'),
                        'kubernetes': source.get('kubernetes', {}),
                        **{k: v for k, v in source.items() if k not in ['@timestamp', 'message', 'level']}
                    }
                )
                logs.append(log)

            logger.info(f"Fetched {len(logs)} logs from Fluentd (Elasticsearch)")

        except Exception as e:
            logger.error(f"Error fetching from Elasticsearch backend: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error logs from Fluentd.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        if filters:
            filters = filters.copy()
            error_query = '(ERROR OR error OR CRITICAL OR critical OR exception OR Exception OR failed)'
            if 'query' in filters:
                filters['query'] = f"{filters['query']} AND {error_query}"
            else:
                filters['query'] = error_query
        else:
            filters = {'query': '(ERROR OR CRITICAL OR exception OR failed)'}

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fluentd can collect metrics but storage depends on backend.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            List of PerformanceMetric objects (if backend supports metrics)
        """
        logger.info("Fluentd metrics depend on storage backend configuration")
        return []

    def send_log(self, tag: str, record: Dict[str, Any]) -> bool:
        """
        Send a log entry to Fluentd HTTP input.

        Args:
            tag: Fluentd tag
            record: Log record as dictionary

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.http_endpoint}/{tag}"

        try:
            response = self.session.post(
                url,
                json=record,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.debug(f"Sent log to Fluentd tag '{tag}'")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending log to Fluentd: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to Fluentd."""
        try:
            # Try to send a test log
            test_record = {'message': 'Connection test', 'level': 'INFO'}
            return self.send_log('test.connection', test_record)

        except Exception as e:
            logger.error(f"Fluentd connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'backend_client') and self.backend_client:
            try:
                self.backend_client.close()
            except:
                pass
