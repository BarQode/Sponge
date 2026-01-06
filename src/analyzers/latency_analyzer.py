"""
Latency Analyzer - Detects latency issues and performance bottlenecks.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import numpy as np
from collections import defaultdict

from src.integrations.base import PerformanceMetric, LogEntry

logger = logging.getLogger(__name__)


class LatencyIssue:
    """Result of latency analysis."""

    def __init__(
        self,
        issue_type: str,
        severity: str,
        description: str,
        affected_resources: List[str],
        metrics: Dict[str, float],
        recommendations: List[str]
    ):
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.affected_resources = affected_resources
        self.metrics = metrics
        self.recommendations = recommendations
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'issue_type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'affected_resources': self.affected_resources,
            'metrics': self.metrics,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat()
        }


class LatencyAnalyzer:
    """
    Analyzes latency metrics to detect:
    - High response times
    - Latency spikes
    - Network latency issues
    - Database query slowness
    - API endpoint performance issues
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Latency analyzer."""
        self.config = config or {}

        # Thresholds (in milliseconds)
        self.high_latency_threshold = self.config.get('high_latency_threshold', 1000)
        self.spike_threshold = self.config.get('spike_threshold', 3000)
        self.p95_threshold = self.config.get('p95_threshold', 2000)

        logger.info("Latency Analyzer initialized")

    def analyze(
        self,
        metrics: List[PerformanceMetric],
        logs: Optional[List[LogEntry]] = None
    ) -> List[LatencyIssue]:
        """Analyze latency metrics and logs."""
        issues = []

        if not metrics:
            logger.warning("No latency metrics provided")
            return issues

        # Group by endpoint/service
        metrics_by_resource = self._group_by_resource(metrics)

        for resource, resource_metrics in metrics_by_resource.items():
            # Detect high latency
            high_latency = self._detect_high_latency(resource, resource_metrics)
            if high_latency:
                issues.append(high_latency)

            # Detect latency spikes
            spikes = self._detect_latency_spikes(resource, resource_metrics)
            if spikes:
                issues.append(spikes)

        # Correlate with timeout errors
        if logs:
            timeout_issues = self._detect_timeout_errors(logs)
            issues.extend(timeout_issues)

        logger.info(f"Latency Analysis complete: found {len(issues)} issues")
        return issues

    def _group_by_resource(self, metrics: List[PerformanceMetric]) -> Dict[str, List[PerformanceMetric]]:
        """Group metrics by resource."""
        grouped = defaultdict(list)
        for metric in metrics:
            resource = metric.dimensions.get('endpoint', metric.dimensions.get('service', 'unknown'))
            grouped[resource].append(metric)
        return dict(grouped)

    def _detect_high_latency(self, resource: str, metrics: List[PerformanceMetric]) -> Optional[LatencyIssue]:
        """Detect sustained high latency."""
        latency_values = [m.value for m in metrics if 'latency' in m.metric_name.lower() or 'response' in m.metric_name.lower()]

        if not latency_values:
            return None

        avg_latency = np.mean(latency_values)
        p95_latency = np.percentile(latency_values, 95)
        max_latency = np.max(latency_values)

        if avg_latency > self.high_latency_threshold or p95_latency > self.p95_threshold:
            return LatencyIssue(
                issue_type='high_latency',
                severity='high' if avg_latency > 2000 else 'medium',
                description=f'High latency detected on {resource}',
                affected_resources=[resource],
                metrics={
                    'average_latency_ms': float(avg_latency),
                    'p95_latency_ms': float(p95_latency),
                    'max_latency_ms': float(max_latency)
                },
                recommendations=[
                    'Profile application code to identify slow operations',
                    'Review database queries and add indexes if needed',
                    'Check for N+1 query problems',
                    'Implement caching for frequently accessed data',
                    'Review external API call patterns and implement circuit breakers',
                    'Check network latency to dependencies',
                    'Optimize large payload sizes',
                    'Consider implementing async processing for long operations'
                ]
            )
        return None

    def _detect_latency_spikes(self, resource: str, metrics: List[PerformanceMetric]) -> Optional[LatencyIssue]:
        """Detect latency spikes."""
        latency_values = [m.value for m in metrics if 'latency' in m.metric_name.lower()]

        if not latency_values or len(latency_values) < 3:
            return None

        std_dev = np.std(latency_values)
        mean = np.mean(latency_values)
        spikes = [v for v in latency_values if v > (mean + 2 * std_dev) and v > self.spike_threshold]

        if spikes:
            return LatencyIssue(
                issue_type='latency_spikes',
                severity='medium',
                description=f'Latency spikes detected on {resource}',
                affected_resources=[resource],
                metrics={
                    'spike_count': len(spikes),
                    'max_spike_ms': float(max(spikes)),
                    'average_latency_ms': float(mean)
                },
                recommendations=[
                    'Investigate cold start issues (serverless functions, connection pools)',
                    'Check for garbage collection pauses',
                    'Review thread pool saturation',
                    'Investigate database connection pool exhaustion',
                    'Check for bursty traffic patterns',
                    'Review resource contention (CPU, memory, I/O)'
                ]
            )
        return None

    def _detect_timeout_errors(self, logs: List[LogEntry]) -> List[LatencyIssue]:
        """Detect timeout errors from logs."""
        timeout_issues = []
        timeout_keywords = ['timeout', 'timed out', 'time out', 'connection timeout', 'read timeout']

        for log in logs:
            if any(keyword in log.message.lower() for keyword in timeout_keywords):
                timeout_issues.append(LatencyIssue(
                    issue_type='timeout_error',
                    severity='high',
                    description=f'Timeout error detected: {log.message[:150]}',
                    affected_resources=[log.source],
                    metrics={},
                    recommendations=[
                        'Increase timeout configuration if operations are legitimately slow',
                        'Optimize the slow operation causing timeouts',
                        'Implement retry logic with exponential backoff',
                        'Check network connectivity and firewall rules',
                        'Review database query performance',
                        'Implement circuit breakers for failing dependencies'
                    ]
                ))

        return timeout_issues
