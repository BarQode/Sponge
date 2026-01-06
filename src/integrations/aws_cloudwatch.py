"""
AWS CloudWatch integration for log and metrics collection.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class CloudWatchIntegration(BaseIntegration):
    """AWS CloudWatch integration for comprehensive monitoring data."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CloudWatch integration.

        Required config keys:
        - aws_access_key_id: AWS access key
        - aws_secret_access_key: AWS secret key
        - aws_region: AWS region (default: us-east-1)
        - log_group_name: CloudWatch log group name
        """
        super().__init__(config)

        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for CloudWatch integration. "
                "Install with: pip install boto3"
            )

        self.region = config.get('aws_region', 'us-east-1')
        self.log_group_name = config.get('log_group_name')

        # Initialize AWS clients
        session = boto3.Session(
            aws_access_key_id=config.get('aws_access_key_id'),
            aws_secret_access_key=config.get('aws_secret_access_key'),
            region_name=self.region
        )

        self.logs_client = session.client('logs')
        self.cloudwatch_client = session.client('cloudwatch')

        logger.info(f"CloudWatch integration initialized for region: {self.region}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch logs from CloudWatch Logs."""
        logs = []
        filters = filters or {}

        try:
            # Convert datetime to milliseconds since epoch
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            log_group = filters.get('log_group', self.log_group_name)
            filter_pattern = filters.get('filter_pattern', '')

            if not log_group:
                logger.error("No log group specified")
                return []

            # Query parameters
            query_params = {
                'logGroupName': log_group,
                'startTime': start_ms,
                'endTime': end_ms
            }

            if filter_pattern:
                query_params['filterPattern'] = filter_pattern

            # Handle pagination
            next_token = None

            while True:
                if next_token:
                    query_params['nextToken'] = next_token

                response = self.logs_client.filter_log_events(**query_params)

                for event in response.get('events', []):
                    log_entry = LogEntry(
                        timestamp=datetime.fromtimestamp(event['timestamp'] / 1000),
                        message=event['message'],
                        level=self._extract_log_level(event['message']),
                        source='cloudwatch',
                        metadata={
                            'log_stream': event.get('logStreamName'),
                            'log_group': log_group,
                            'event_id': event.get('eventId')
                        }
                    )
                    logs.append(log_entry)

                next_token = response.get('nextToken')
                if not next_token:
                    break

            logger.info(f"Fetched {len(logs)} logs from CloudWatch")
            return logs

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error fetching CloudWatch logs: {e}")
            return []

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch error logs specifically."""
        filters = filters or {}
        # Add error filter pattern
        error_patterns = [
            '"ERROR"', '"Error"', '"CRITICAL"', '"FATAL"',
            '"Exception"', '"Failed"', '"Failure"'
        ]
        filters['filter_pattern'] = ' '.join(error_patterns)

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """Fetch performance metrics from CloudWatch."""
        metrics = []

        # Default metrics to fetch if not specified
        if not metric_names:
            metric_names = [
                'CPUUtilization',
                'MemoryUtilization',
                'NetworkIn',
                'NetworkOut',
                'DiskReadBytes',
                'DiskWriteBytes'
            ]

        try:
            for metric_name in metric_names:
                response = self.cloudwatch_client.get_metric_statistics(
                    Namespace='AWS/EC2',  # Can be parameterized
                    MetricName=metric_name,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,  # 5 minutes
                    Statistics=['Average', 'Maximum']
                )

                for datapoint in response.get('Datapoints', []):
                    metric = PerformanceMetric(
                        metric_name=metric_name,
                        value=datapoint.get('Average', 0),
                        unit=datapoint.get('Unit', 'None'),
                        timestamp=datapoint['Timestamp'],
                        dimensions={'stat': 'average'}
                    )
                    metrics.append(metric)

            logger.info(f"Fetched {len(metrics)} metrics from CloudWatch")
            return metrics

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error fetching CloudWatch metrics: {e}")
            return []

    @staticmethod
    def _extract_log_level(message: str) -> str:
        """Extract log level from message."""
        message_upper = message.upper()
        for level in ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG']:
            if level in message_upper:
                return level
        return 'INFO'
