"""
Memory Analyzer - Detects memory leaks, high memory usage, and zombie processes consuming memory.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import numpy as np
from collections import defaultdict

from src.integrations.base import PerformanceMetric, LogEntry

logger = logging.getLogger(__name__)


class MemoryIssue:
    """Result of memory analysis."""

    def __init__(
        self,
        issue_type: str,
        severity: str,
        description: str,
        affected_resources: List[str],
        metrics: Dict[str, float],
        recommendations: List[str],
        potential_zombie: bool = False
    ):
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.affected_resources = affected_resources
        self.metrics = metrics
        self.recommendations = recommendations
        self.potential_zombie = potential_zombie
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'issue_type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'affected_resources': self.affected_resources,
            'metrics': self.metrics,
            'recommendations': self.recommendations,
            'potential_zombie': self.potential_zombie,
            'timestamp': self.timestamp.isoformat()
        }


class MemoryAnalyzer:
    """
    Analyzes memory usage patterns to detect:
    - Memory leaks (gradually increasing memory)
    - High memory usage
    - OOM (Out of Memory) conditions
    - Zombie processes holding memory
    - Memory fragmentation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Memory analyzer."""
        self.config = config or {}

        # Thresholds
        self.high_memory_threshold = self.config.get('high_memory_threshold', 85.0)
        self.leak_correlation_threshold = self.config.get('leak_correlation_threshold', 0.8)
        self.leak_min_increase = self.config.get('leak_min_increase', 15.0)  # percent

        logger.info("Memory Analyzer initialized")

    def analyze(
        self,
        metrics: List[PerformanceMetric],
        logs: Optional[List[LogEntry]] = None
    ) -> List[MemoryIssue]:
        """
        Analyze memory metrics and logs to identify issues.

        Args:
            metrics: List of memory performance metrics
            logs: Optional log entries for correlation

        Returns:
            List of MemoryIssue results
        """
        issues = []

        if not metrics:
            logger.warning("No memory metrics provided for analysis")
            return issues

        # Group metrics by resource
        metrics_by_resource = self._group_by_resource(metrics)

        for resource, resource_metrics in metrics_by_resource.items():
            # Detect memory leaks
            leak = self._detect_memory_leak(resource, resource_metrics)
            if leak:
                issues.append(leak)

            # Detect high memory usage
            high_mem = self._detect_high_memory(resource, resource_metrics)
            if high_mem:
                issues.append(high_mem)

            # Detect potential zombies
            zombie = self._detect_zombie_process(resource, resource_metrics)
            if zombie:
                issues.append(zombie)

        # Correlate with OOM errors in logs
        if logs:
            oom_issues = self._detect_oom_from_logs(logs)
            issues.extend(oom_issues)

        logger.info(f"Memory Analysis complete: found {len(issues)} issues")
        return issues

    def _group_by_resource(
        self,
        metrics: List[PerformanceMetric]
    ) -> Dict[str, List[PerformanceMetric]]:
        """Group metrics by resource identifier."""
        grouped = defaultdict(list)

        for metric in metrics:
            resource = metric.dimensions.get('host', metric.dimensions.get('service', 'unknown'))
            grouped[resource].append(metric)

        return dict(grouped)

    def _detect_memory_leak(
        self,
        resource: str,
        metrics: List[PerformanceMetric]
    ) -> Optional[MemoryIssue]:
        """Detect memory leaks through gradual memory increase."""
        memory_values = [
            m.value for m in metrics
            if 'mem' in m.metric_name.lower() or 'memory' in m.metric_name.lower()
        ]

        if not memory_values or len(memory_values) < 10:
            return None

        # Sort by timestamp to ensure chronological order
        sorted_metrics = sorted(
            [m for m in metrics if 'mem' in m.metric_name.lower()],
            key=lambda x: x.timestamp
        )
        memory_values = [m.value for m in sorted_metrics]

        # Calculate correlation with time (indicates linear increase)
        x = np.arange(len(memory_values))
        correlation = np.corrcoef(x, memory_values)[0, 1]

        # Calculate percentage increase
        start_val = memory_values[0]
        end_val = memory_values[-1]
        percent_increase = ((end_val - start_val) / start_val) * 100 if start_val > 0 else 0

        # Memory leak detected if strong correlation and significant increase
        if correlation > self.leak_correlation_threshold and percent_increase > self.leak_min_increase:
            return MemoryIssue(
                issue_type='memory_leak',
                severity='critical',
                description=f'Memory leak detected on {resource}',
                affected_resources=[resource],
                metrics={
                    'correlation': float(correlation),
                    'percent_increase': float(percent_increase),
                    'start_memory': float(start_val),
                    'end_memory': float(end_val),
                    'duration_hours': len(memory_values) / 12  # Assuming 5-min intervals
                },
                recommendations=[
                    'Enable heap dump analysis to identify leaking objects',
                    'Review recent code changes for resource cleanup issues',
                    'Check for unclosed file handles or database connections',
                    'Investigate static collections or caches that grow unbounded',
                    'Review event listeners and callbacks for proper cleanup',
                    'Check for circular references preventing garbage collection',
                    'Consider implementing memory profiling in production',
                    'Review third-party library versions for known memory leaks'
                ],
                potential_zombie=False
            )

        return None

    def _detect_high_memory(
        self,
        resource: str,
        metrics: List[PerformanceMetric]
    ) -> Optional[MemoryIssue]:
        """Detect sustained high memory usage."""
        memory_values = [
            m.value for m in metrics
            if 'mem' in m.metric_name.lower() or 'memory' in m.metric_name.lower()
        ]

        if not memory_values:
            return None

        avg_memory = np.mean(memory_values)
        max_memory = np.max(memory_values)

        if avg_memory > self.high_memory_threshold:
            return MemoryIssue(
                issue_type='high_memory_usage',
                severity='high' if avg_memory > 95 else 'medium',
                description=f'High memory usage detected on {resource}',
                affected_resources=[resource],
                metrics={
                    'average_memory': float(avg_memory),
                    'max_memory': float(max_memory),
                    'threshold': self.high_memory_threshold
                },
                recommendations=[
                    'Identify processes with highest memory consumption',
                    'Review application memory configuration (heap size, etc.)',
                    'Consider increasing available memory or scaling horizontally',
                    'Analyze heap dumps to identify large objects',
                    'Review caching strategies and cache eviction policies',
                    'Check for large in-memory data structures',
                    'Investigate database result set sizes'
                ],
                potential_zombie=False
            )

        return None

    def _detect_zombie_process(
        self,
        resource: str,
        metrics: List[PerformanceMetric]
    ) -> Optional[MemoryIssue]:
        """
        Detect zombie processes - processes consuming memory but doing no work.
        Indicated by constant memory usage with low/no CPU activity.
        """
        memory_values = [
            m.value for m in metrics
            if 'mem' in m.metric_name.lower()
        ]

        if not memory_values or len(memory_values) < 5:
            return None

        # Check if memory is consistently high but not increasing (zombie signature)
        memory_std = np.std(memory_values)
        memory_mean = np.mean(memory_values)

        # Low variance + high memory = potential zombie
        if memory_mean > 50 and memory_std < 5:
            return MemoryIssue(
                issue_type='zombie_process',
                severity='medium',
                description=f'Potential zombie process detected on {resource}',
                affected_resources=[resource],
                metrics={
                    'average_memory': float(memory_mean),
                    'memory_std_dev': float(memory_std)
                },
                recommendations=[
                    'Identify processes with constant memory usage and no CPU activity',
                    'Check for hung or deadlocked processes',
                    'Review process list for defunct or zombie processes',
                    'Investigate processes waiting indefinitely on I/O',
                    'Check for processes blocked on network operations',
                    'Review application lifecycle and shutdown procedures',
                    'Consider implementing health checks and auto-restart mechanisms'
                ],
                potential_zombie=True
            )

        return None

    def _detect_oom_from_logs(self, logs: List[LogEntry]) -> List[MemoryIssue]:
        """Detect Out of Memory errors from logs."""
        oom_issues = []

        oom_keywords = [
            'outofmemoryerror',
            'out of memory',
            'oom',
            'memory allocation failed',
            'cannot allocate memory',
            'java heap space'
        ]

        for log in logs:
            message_lower = log.message.lower()

            if any(keyword in message_lower for keyword in oom_keywords):
                oom_issues.append(MemoryIssue(
                    issue_type='out_of_memory',
                    severity='critical',
                    description=f'Out of Memory error detected: {log.message[:150]}',
                    affected_resources=[log.source],
                    metrics={},
                    recommendations=[
                        'Immediately investigate heap dump from time of OOM',
                        'Increase heap size if legitimate memory requirement',
                        'Identify and fix memory leak if present',
                        'Review large object allocations',
                        'Check for bulk operations loading too much data',
                        'Implement pagination for large data sets',
                        'Review garbage collection logs and configuration'
                    ],
                    potential_zombie=False
                ))

        return oom_issues
