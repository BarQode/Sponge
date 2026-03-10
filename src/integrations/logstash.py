"""
Logstash Integration for Log Retrieval.

Connects to Logstash via HTTP input plugin or Elasticsearch output.
Supports structured log ingestion and retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter, Retry
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class LogstashIntegration(BaseIntegration):
    """
    Integration with Logstash for log retrieval.

    Features:
    - HTTP input plugin support
    - Elasticsearch backend querying
    - Structured log parsing
    - Pipeline filtering
    - Connection pooling

    Note: Logstash itself doesn't store logs - it processes and forwards them.
    This integration queries the Elasticsearch backend or sends to HTTP input.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Logstash integration.

        Args:
            config: Configuration dict with:
                - http_endpoint: Logstash HTTP input endpoint
                - elasticsearch_hosts: Elasticsearch backend hosts
                - index_pattern: Elasticsearch index pattern (default: 'logstash-*')
                - timeout: Request timeout (default: 30)
        """
        super().__init__(config)
        self.http_endpoint = config.get('http_endpoint', 'http://localhost:8080')
        self.es_hosts = config.get('elasticsearch_hosts', ['http://localhost:9200'])
        self.index_pattern = config.get('index_pattern', 'logstash-*')
        self.timeout = config.get('timeout', 30)

        # Create HTTP session for Logstash input
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

        # Initialize Elasticsearch client for querying
        self.es_client = None
        self._init_elasticsearch_client()

        logger.info(f"Logstash integration initialized")

    def _init_elasticsearch_client(self):
        """Initialize Elasticsearch client for querying Logstash output."""
        try:
            from elasticsearch import Elasticsearch

            self.es_client = Elasticsearch(
                hosts=self.es_hosts,
                request_timeout=self.timeout
            )
            logger.info(f"Initialized Elasticsearch client for Logstash: {self.es_hosts}")

        except ImportError:
            logger.warning("Elasticsearch library not installed - install with: pip install elasticsearch")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch client: {e}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Logstash (via Elasticsearch backend).

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (query, fields, pipeline)

        Returns:
            List of LogEntry objects
        """
        if not self.es_client:
            logger.error("Elasticsearch client not initialized - cannot fetch logs")
            return []

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
                },
                "sort": [
                    {"@timestamp": {"order": "desc"}}
                ]
            }

            # Add custom query if specified
            if filters and 'query' in filters:
                query["query"]["bool"]["must"].append({
                    "query_string": {"query": filters['query']}
                })

            # Add field filters
            if filters and 'fields' in filters:
                for field, value in filters['fields'].items():
                    query["query"]["bool"]["must"].append({
                        "match": {field: value}
                    })

            index = filters.get('index', self.index_pattern) if filters else self.index_pattern
            size = filters.get('size', 1000) if filters else 1000

            # Execute search
            response = self.es_client.search(
                index=index,
                body=query,
                size=size
            )

            for hit in response['hits']['hits']:
                source = hit['_source']

                log = LogEntry(
                    timestamp=datetime.fromisoformat(
                        source.get('@timestamp', '').replace('Z', '+00:00')
                    ),
                    message=source.get('message', ''),
                    level=self._extract_level(source),
                    source='logstash',
                    metadata={
                        'host': source.get('host', {}),
                        'agent': source.get('agent', {}),
                        'tags': source.get('tags', []),
                        'fields': source.get('fields', {}),
                        **{k: v for k, v in source.items()
                           if k not in ['@timestamp', 'message', '@version']}
                    }
                )
                logs.append(log)

            logger.info(f"Fetched {len(logs)} logs from Logstash (Elasticsearch)")

        except Exception as e:
            logger.error(f"Error fetching Logstash logs: {e}")

        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error logs from Logstash.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        if filters:
            filters = filters.copy()
            error_query = '(level:ERROR OR level:CRITICAL OR ERROR OR CRITICAL OR exception OR failed)'
            if 'query' in filters:
                filters['query'] = f"{filters['query']} AND {error_query}"
            else:
                filters['query'] = error_query
        else:
            filters = {'query': '(level:ERROR OR level:CRITICAL OR ERROR OR CRITICAL OR exception)'}

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Logstash can process metric data but storage depends on output configuration.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to query

        Returns:
            List of PerformanceMetric objects (if Elasticsearch contains metric data)
        """
        logger.info("Logstash metrics depend on pipeline and output configuration")
        return []

    def _extract_level(self, log_data: Dict[str, Any]) -> str:
        """Extract log level from log data."""
        # Check common level fields
        level = log_data.get('level', log_data.get('loglevel', log_data.get('severity', ''))).upper()

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

        # Infer from message
        message = log_data.get('message', '').lower()
        if any(word in message for word in ['critical', 'fatal']):
            return 'CRITICAL'
        elif any(word in message for word in ['error', 'exception']):
            return 'ERROR'
        elif any(word in message for word in ['warning', 'warn']):
            return 'WARNING'

        return 'INFO'

    def send_log(self, log_data: Dict[str, Any]) -> bool:
        """
        Send a log entry to Logstash HTTP input.

        Args:
            log_data: Log data as dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(
                self.http_endpoint,
                json=log_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.debug("Sent log to Logstash HTTP input")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending log to Logstash: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to Logstash."""
        try:
            # Test Elasticsearch connection
            if self.es_client:
                self.es_client.ping()
                logger.info("Logstash connection test (Elasticsearch): SUCCESS")
                return True
            else:
                logger.warning("Elasticsearch client not available")
                return False

        except Exception as e:
            logger.error(f"Logstash connection test FAILED: {e}")
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'es_client') and self.es_client:
            try:
                self.es_client.close()
            except:
                pass
