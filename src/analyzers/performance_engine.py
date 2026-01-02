"""
Unified Performance Analysis Engine - Orchestrates all analyzers.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric
from src.analyzers.cpu_analyzer import CPUAnalyzer, CPUAnalysis
from src.analyzers.memory_analyzer import MemoryAnalyzer, MemoryIssue
from src.analyzers.latency_analyzer import LatencyAnalyzer, LatencyIssue
from src.analyzers.zombie_detector import ZombieDetector, ZombieDetection

logger = logging.getLogger(__name__)


class PerformanceReport:
    """Complete performance analysis report."""

    def __init__(self):
        self.cpu_issues: List[CPUAnalysis] = []
        self.memory_issues: List[MemoryIssue] = []
        self.latency_issues: List[LatencyIssue] = []
        self.zombie_detections: List[ZombieDetection] = []
        self.error_logs: List[LogEntry] = []
        self.timestamp = datetime.utcnow()

    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all issues as a unified list."""
        all_issues = []

        for issue in self.cpu_issues:
            all_issues.append({
                'category': 'CPU',
                **issue.to_dict()
            })

        for issue in self.memory_issues:
            all_issues.append({
                'category': 'Memory',
                **issue.to_dict()
            })

        for issue in self.latency_issues:
            all_issues.append({
                'category': 'Latency',
                **issue.to_dict()
            })

        for detection in self.zombie_detections:
            all_issues.append({
                'category': 'Zombie',
                **detection.to_dict()
            })

        return all_issues

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            'total_issues': (
                len(self.cpu_issues) +
                len(self.memory_issues) +
                len(self.latency_issues) +
                len(self.zombie_detections)
            ),
            'cpu_issues': len(self.cpu_issues),
            'memory_issues': len(self.memory_issues),
            'latency_issues': len(self.latency_issues),
            'zombie_detections': len(self.zombie_detections),
            'error_logs': len(self.error_logs),
            'severity_breakdown': self._get_severity_breakdown(),
            'timestamp': self.timestamp.isoformat()
        }

    def _get_severity_breakdown(self) -> Dict[str, int]:
        """Get count of issues by severity."""
        severity_count = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

        all_issues = self.get_all_issues()
        for issue in all_issues:
            severity = issue.get('severity', 'medium').lower()
            if severity in severity_count:
                severity_count[severity] += 1

        return severity_count


class PerformanceAnalysisEngine:
    """
    Unified engine for comprehensive performance analysis.

    Orchestrates:
    - Data collection from monitoring platforms
    - CPU, Memory, Latency analysis
    - Zombie process detection
    - Error correlation
    - Report generation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the performance analysis engine."""
        self.config = config or {}

        # Initialize analyzers
        self.cpu_analyzer = CPUAnalyzer(self.config.get('cpu', {}))
        self.memory_analyzer = MemoryAnalyzer(self.config.get('memory', {}))
        self.latency_analyzer = LatencyAnalyzer(self.config.get('latency', {}))
        self.zombie_detector = ZombieDetector(self.config.get('zombie', {}))

        logger.info("Performance Analysis Engine initialized")

    def analyze_from_integration(
        self,
        integration: BaseIntegration,
        hours: int = 24
    ) -> PerformanceReport:
        """
        Perform complete analysis from a monitoring platform integration.

        Args:
            integration: Monitoring platform integration
            hours: Hours of data to analyze

        Returns:
            Complete PerformanceReport
        """
        logger.info(f"Starting performance analysis for last {hours} hours")

        report = PerformanceReport()

        try:
            # Fetch data from integration
            logs = integration.fetch_recent_logs(hours=hours)
            errors = integration.fetch_recent_errors(hours=hours)
            metrics = integration.fetch_performance_metrics(
                start_time=datetime.utcnow() - timedelta(hours=hours),
                end_time=datetime.utcnow()
            )

            # Run analyses
            report.cpu_issues = self.cpu_analyzer.analyze(metrics, logs)
            report.memory_issues = self.memory_analyzer.analyze(metrics, logs)
            report.latency_issues = self.latency_analyzer.analyze(metrics, logs)
            report.zombie_detections = self.zombie_detector.analyze(logs)
            report.error_logs = errors

            logger.info(f"Analysis complete. Found {len(report.get_all_issues())} total issues")

        except Exception as e:
            logger.error(f"Error during performance analysis: {e}", exc_info=True)

        return report

    def analyze_from_data(
        self,
        logs: List[LogEntry],
        metrics: List[PerformanceMetric]
    ) -> PerformanceReport:
        """
        Perform analysis from pre-collected data.

        Args:
            logs: Log entries
            metrics: Performance metrics

        Returns:
            PerformanceReport
        """
        report = PerformanceReport()

        try:
            # Run all analyses
            report.cpu_issues = self.cpu_analyzer.analyze(metrics, logs)
            report.memory_issues = self.memory_analyzer.analyze(metrics, logs)
            report.latency_issues = self.latency_analyzer.analyze(metrics, logs)
            report.zombie_detections = self.zombie_detector.analyze(logs)
            report.error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]

            logger.info(f"Analysis complete. Found {len(report.get_all_issues())} total issues")

        except Exception as e:
            logger.error(f"Error during analysis: {e}", exc_info=True)

        return report
