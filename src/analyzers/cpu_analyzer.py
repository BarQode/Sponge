"""
CPU Usage Analyzer - Detects unnecessary CPU usage and performance issues.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import numpy as np
from collections import defaultdict

from src.integrations.base import PerformanceMetric, LogEntry

logger = logging.getLogger(__name__)


class CPUAnalysis:
    """Result of CPU analysis."""

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


class CPUAnalyzer:
    """
    Analyzes CPU usage patterns to detect:
    - High CPU usage
    - CPU spikes
    - Inefficient processes
    - Runaway processes
    - CPU throttling
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CPU analyzer.

        Args:
            config: Configuration with thresholds
        """
        self.config = config or {}

        # Thresholds
        self.high_cpu_threshold = self.config.get('high_cpu_threshold', 80.0)
        self.sustained_high_duration = self.config.get('sustained_high_duration', 300)  # seconds
        self.spike_threshold = self.config.get('spike_threshold', 95.0)

        logger.info("CPU Analyzer initialized")

    def analyze(
        self,
        metrics: List[PerformanceMetric],
        logs: Optional[List[LogEntry]] = None
    ) -> List[CPUAnalysis]:
        """
        Analyze CPU metrics and logs to identify issues.

        Args:
            metrics: List of CPU performance metrics
            logs: Optional log entries for correlation

        Returns:
            List of CPUAnalysis results
        """
        issues = []

        if not metrics:
            logger.warning("No CPU metrics provided for analysis")
            return issues

        # Group metrics by resource (host/service)
        metrics_by_resource = self._group_by_resource(metrics)

        for resource, resource_metrics in metrics_by_resource.items():
            # Detect high sustained CPU usage
            high_cpu = self._detect_high_cpu(resource, resource_metrics)
            if high_cpu:
                issues.append(high_cpu)

            # Detect CPU spikes
            cpu_spikes = self._detect_cpu_spikes(resource, resource_metrics)
            if cpu_spikes:
                issues.append(cpu_spikes)

            # Detect unusual patterns
            unusual = self._detect_unusual_patterns(resource, resource_metrics)
            if unusual:
                issues.append(unusual)

        # Correlate with logs if available
        if logs:
            correlated = self._correlate_with_logs(issues, logs)
            issues.extend(correlated)

        logger.info(f"CPU Analysis complete: found {len(issues)} issues")
        return issues

    def _group_by_resource(
        self,
        metrics: List[PerformanceMetric]
    ) -> Dict[str, List[PerformanceMetric]]:
        """Group metrics by resource identifier."""
        grouped = defaultdict(list)

        for metric in metrics:
            # Use dimensions to identify resource
            resource = metric.dimensions.get('host', metric.dimensions.get('service', 'unknown'))
            grouped[resource].append(metric)

        return dict(grouped)

    def _detect_high_cpu(
        self,
        resource: str,
        metrics: List[PerformanceMetric]
    ) -> Optional[CPUAnalysis]:
        """Detect sustained high CPU usage."""
        values = [m.value for m in metrics if m.metric_name.lower().find('cpu') != -1]

        if not values:
            return None

        avg_cpu = np.mean(values)
        max_cpu = np.max(values)

        if avg_cpu > self.high_cpu_threshold:
            return CPUAnalysis(
                issue_type='high_cpu_usage',
                severity='high' if avg_cpu > 90 else 'medium',
                description=f'Sustained high CPU usage detected on {resource}',
                affected_resources=[resource],
                metrics={
                    'average_cpu': float(avg_cpu),
                    'max_cpu': float(max_cpu),
                    'threshold': self.high_cpu_threshold
                },
                recommendations=[
                    'Identify and optimize CPU-intensive processes',
                    'Consider scaling horizontally if load is legitimate',
                    'Review recent code deployments for performance regressions',
                    'Check for infinite loops or inefficient algorithms',
                    'Monitor thread counts and investigate thread contention'
                ]
            )

        return None

    def _detect_cpu_spikes(
        self,
        resource: str,
        metrics: List[PerformanceMetric]
    ) -> Optional[CPUAnalysis]:
        """Detect CPU spikes."""
        values = [m.value for m in metrics if m.metric_name.lower().find('cpu') != -1]

        if not values or len(values) < 3:
            return None

        # Calculate standard deviation to find spikes
        std_dev = np.std(values)
        mean = np.mean(values)

        spikes = [v for v in values if v > (mean + 2 * std_dev) and v > self.spike_threshold]

        if spikes:
            return CPUAnalysis(
                issue_type='cpu_spikes',
                severity='medium',
                description=f'CPU spikes detected on {resource}',
                affected_resources=[resource],
                metrics={
                    'spike_count': len(spikes),
                    'max_spike': float(max(spikes)),
                    'average': float(mean),
                    'std_dev': float(std_dev)
                },
                recommendations=[
                    'Investigate processes causing sudden CPU bursts',
                    'Check for batch jobs or scheduled tasks',
                    'Review application request patterns',
                    'Consider implementing rate limiting',
                    'Check for resource-intensive cron jobs or background tasks'
                ]
            )

        return None

    def _detect_unusual_patterns(
        self,
        resource: str,
        metrics: List[PerformanceMetric]
    ) -> Optional[CPUAnalysis]:
        """Detect unusual CPU usage patterns."""
        values = [m.value for m in metrics if m.metric_name.lower().find('cpu') != -1]

        if not values or len(values) < 10:
            return None

        # Check for gradually increasing CPU (potential memory leak causing GC pressure)
        if self._is_gradually_increasing(values):
            return CPUAnalysis(
                issue_type='gradually_increasing_cpu',
                severity='medium',
                description=f'Gradually increasing CPU usage on {resource} - possible memory leak',
                affected_resources=[resource],
                metrics={
                    'start_value': float(values[0]),
                    'end_value': float(values[-1]),
                    'increase': float(values[-1] - values[0])
                },
                recommendations=[
                    'Check for memory leaks causing increased garbage collection',
                    'Review application memory usage trends',
                    'Investigate file descriptor leaks',
                    'Check for accumulating in-memory caches',
                    'Review database connection pooling'
                ]
            )

        return None

    @staticmethod
    def _is_gradually_increasing(values: List[float], threshold: float = 0.7) -> bool:
        """Check if values show a gradually increasing trend."""
        if len(values) < 5:
            return False

        # Calculate correlation coefficient with time
        x = np.arange(len(values))
        correlation = np.corrcoef(x, values)[0, 1]

        return correlation > threshold and values[-1] > values[0] + 10

    def _correlate_with_logs(
        self,
        cpu_issues: List[CPUAnalysis],
        logs: List[LogEntry]
    ) -> List[CPUAnalysis]:
        """Correlate CPU issues with error logs."""
        additional_issues = []

        # Look for specific error patterns
        error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]

        cpu_related_keywords = [
            'timeout', 'slow', 'performance', 'bottleneck',
            'thread', 'deadlock', 'lock', 'blocked'
        ]

        for log in error_logs:
            if any(keyword in log.message.lower() for keyword in cpu_related_keywords):
                # Found a potentially CPU-related error
                additional_issues.append(CPUAnalysis(
                    issue_type='cpu_related_error',
                    severity='high',
                    description=f'CPU-related error detected: {log.message[:100]}',
                    affected_resources=[log.source],
                    metrics={},
                    recommendations=[
                        'Investigate the specific error in application logs',
                        'Check for thread deadlocks or contention',
                        'Review database query performance',
                        'Profile the application to identify bottlenecks'
                    ]
                ))

        return additional_issues
