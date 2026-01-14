"""
Toil Tracker - Identifies and measures manual, repetitive work

Tracks work that is:
- Manual
- Repetitive
- Automatable
- Tactical
- Devoid of enduring value
- Scales linearly with service growth
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToilMetrics:
    """Metrics for tracking toil over time"""
    total_time_spent: float  # hours
    manual_interventions: int
    recurring_count: int
    automation_potential_score: float  # 0-100
    time_period: str
    top_toil_tasks: List[Dict[str, Any]]
    toil_percentage: float  # percentage of total engineering time


class ToilTracker:
    """
    Tracks and analyzes toil in operations

    Integrates with ticketing systems to identify patterns and
    measure the impact of manual work.
    """

    def __init__(self, db_path: str = "data/toil_tracking.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for toil tracking"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS toil_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    time_spent REAL NOT NULL,
                    is_manual BOOLEAN NOT NULL,
                    is_repetitive BOOLEAN NOT NULL,
                    is_automatable BOOLEAN NOT NULL,
                    frequency_per_week REAL,
                    automation_difficulty TEXT,
                    business_impact TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    automated_at TIMESTAMP NULL,
                    automation_savings REAL DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS toil_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT NOT NULL,
                    task_ids TEXT NOT NULL,
                    occurrence_count INTEGER NOT NULL,
                    total_time_spent REAL NOT NULL,
                    automation_priority INTEGER NOT NULL,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def track_task(self,
                   task_id: str,
                   title: str,
                   category: str,
                   time_spent: float,
                   description: str = "",
                   is_manual: bool = True,
                   is_repetitive: bool = False,
                   is_automatable: bool = True,
                   frequency_per_week: float = 0,
                   automation_difficulty: str = "medium",
                   business_impact: str = "medium") -> bool:
        """
        Track a toil task

        Args:
            task_id: Unique identifier (e.g., JIRA ticket ID)
            title: Task title
            category: Category of work (e.g., 'provisioning', 'restart', 'disk_cleanup')
            time_spent: Time spent in hours
            description: Detailed description
            is_manual: Whether task requires manual intervention
            is_repetitive: Whether task occurs regularly
            is_automatable: Whether task can be automated
            frequency_per_week: How often this occurs per week
            automation_difficulty: 'easy', 'medium', 'hard'
            business_impact: 'low', 'medium', 'high', 'critical'

        Returns:
            True if tracked successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO toil_tasks
                    (task_id, title, description, category, time_spent, is_manual,
                     is_repetitive, is_automatable, frequency_per_week,
                     automation_difficulty, business_impact)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (task_id, title, description, category, time_spent, is_manual,
                      is_repetitive, is_automatable, frequency_per_week,
                      automation_difficulty, business_impact))
                conn.commit()

            logger.info(f"Tracked toil task: {task_id} - {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to track toil task: {e}")
            return False

    def mark_automated(self, task_id: str, time_savings: float) -> bool:
        """
        Mark a toil task as automated

        Args:
            task_id: Task identifier
            time_savings: Hours saved per week through automation

        Returns:
            True if updated successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE toil_tasks
                    SET automated_at = CURRENT_TIMESTAMP,
                        automation_savings = ?
                    WHERE task_id = ?
                """, (time_savings, task_id))
                conn.commit()

            logger.info(f"Marked task {task_id} as automated with {time_savings}h/week savings")
            return True
        except Exception as e:
            logger.error(f"Failed to mark task as automated: {e}")
            return False

    def identify_patterns(self, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """
        Identify repetitive patterns in toil tasks

        Args:
            min_occurrences: Minimum number of similar tasks to form a pattern

        Returns:
            List of identified patterns with automation recommendations
        """
        patterns = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Find tasks grouped by category with high repetition
                cursor = conn.execute("""
                    SELECT category, COUNT(*) as count, SUM(time_spent) as total_time,
                           AVG(frequency_per_week) as avg_frequency,
                           GROUP_CONCAT(task_id) as task_ids
                    FROM toil_tasks
                    WHERE is_repetitive = 1 AND automated_at IS NULL
                    GROUP BY category
                    HAVING count >= ?
                    ORDER BY total_time DESC
                """, (min_occurrences,))

                for row in cursor.fetchall():
                    category, count, total_time, avg_freq, task_ids = row

                    # Calculate automation priority (0-100)
                    priority = min(100, int(
                        (total_time * 10) +  # Time impact
                        (count * 5) +  # Frequency impact
                        (avg_freq or 0) * 3  # Weekly frequency impact
                    ))

                    pattern = {
                        'pattern_name': f"Repetitive {category} tasks",
                        'category': category,
                        'occurrence_count': count,
                        'total_time_spent': total_time,
                        'average_frequency_per_week': avg_freq or 0,
                        'task_ids': task_ids.split(','),
                        'automation_priority': priority,
                        'estimated_monthly_savings': total_time * 4,  # Approximate monthly savings
                        'recommendation': self._get_automation_recommendation(category, count, total_time)
                    }

                    patterns.append(pattern)

                    # Store pattern in database
                    conn.execute("""
                        INSERT INTO toil_patterns
                        (pattern_name, task_ids, occurrence_count, total_time_spent, automation_priority)
                        VALUES (?, ?, ?, ?, ?)
                    """, (pattern['pattern_name'], task_ids, count, total_time, priority))

                conn.commit()

            logger.info(f"Identified {len(patterns)} toil patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to identify patterns: {e}")
            return []

    def _get_automation_recommendation(self, category: str, count: int, total_time: float) -> str:
        """Generate automation recommendation based on toil analysis"""
        if total_time > 20:
            urgency = "HIGH PRIORITY"
        elif total_time > 10:
            urgency = "MEDIUM PRIORITY"
        else:
            urgency = "LOW PRIORITY"

        recommendations = {
            'provisioning': "Implement self-service portal with Terraform/Backstage",
            'restart': "Implement auto-restart with health checks and runbook automation",
            'disk_cleanup': "Implement automated disk cleanup with threshold monitoring",
            'deployment': "Implement CI/CD pipeline with automated deployments",
            'backup': "Implement automated backup scheduling with verification",
            'scaling': "Implement auto-scaling based on metrics",
            'monitoring': "Implement automated alerting with runbook actions",
            'access_grant': "Implement JIT access control with ChatOps",
            'certificate': "Implement automated certificate renewal",
            'log_analysis': "Implement automated log aggregation and analysis"
        }

        specific_rec = recommendations.get(category, "Implement automation via runbook or self-service")

        return f"[{urgency}] {specific_rec}. Occurring {count} times, consuming {total_time:.1f} hours."

    def get_metrics(self, days: int = 14) -> ToilMetrics:
        """
        Calculate toil metrics for a time period

        Args:
            days: Number of days to analyze

        Returns:
            ToilMetrics object with comprehensive analysis
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                since_date = datetime.now() - timedelta(days=days)

                # Get total toil time
                cursor = conn.execute("""
                    SELECT SUM(time_spent), COUNT(*),
                           SUM(CASE WHEN is_repetitive = 1 THEN 1 ELSE 0 END)
                    FROM toil_tasks
                    WHERE timestamp >= ?
                """, (since_date,))

                total_time, total_count, repetitive_count = cursor.fetchone()
                total_time = total_time or 0
                total_count = total_count or 0
                repetitive_count = repetitive_count or 0

                # Get top toil tasks
                cursor = conn.execute("""
                    SELECT task_id, title, category, time_spent, frequency_per_week
                    FROM toil_tasks
                    WHERE timestamp >= ?
                    ORDER BY time_spent DESC
                    LIMIT 10
                """, (since_date,))

                top_tasks = [
                    {
                        'task_id': row[0],
                        'title': row[1],
                        'category': row[2],
                        'time_spent': row[3],
                        'frequency_per_week': row[4] or 0
                    }
                    for row in cursor.fetchall()
                ]

                # Calculate automation potential (0-100)
                cursor = conn.execute("""
                    SELECT AVG(
                        CASE
                            WHEN is_automatable = 1 AND is_repetitive = 1 THEN 100
                            WHEN is_automatable = 1 THEN 70
                            WHEN is_repetitive = 1 THEN 50
                            ELSE 20
                        END
                    )
                    FROM toil_tasks
                    WHERE timestamp >= ?
                """, (since_date,))

                automation_score = cursor.fetchone()[0] or 0

                # Assume 40 hours/week * (days/7) as total engineering time
                total_engineering_time = 40 * (days / 7)
                toil_percentage = (total_time / total_engineering_time * 100) if total_engineering_time > 0 else 0

                return ToilMetrics(
                    total_time_spent=total_time,
                    manual_interventions=total_count,
                    recurring_count=repetitive_count,
                    automation_potential_score=automation_score,
                    time_period=f"Last {days} days",
                    top_toil_tasks=top_tasks,
                    toil_percentage=min(100, toil_percentage)
                )

        except Exception as e:
            logger.error(f"Failed to calculate metrics: {e}")
            return ToilMetrics(
                total_time_spent=0,
                manual_interventions=0,
                recurring_count=0,
                automation_potential_score=0,
                time_period=f"Last {days} days",
                top_toil_tasks=[],
                toil_percentage=0
            )

    def export_report(self, output_path: str, days: int = 14) -> bool:
        """
        Export toil analysis report

        Args:
            output_path: Path to save JSON report
            days: Days to analyze

        Returns:
            True if export successful
        """
        try:
            metrics = self.get_metrics(days)
            patterns = self.identify_patterns()

            report = {
                'generated_at': datetime.now().isoformat(),
                'analysis_period': f"Last {days} days",
                'summary': asdict(metrics),
                'patterns': patterns,
                'recommendations': [p['recommendation'] for p in patterns[:5]]
            }

            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Exported toil report to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return False
