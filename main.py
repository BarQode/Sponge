#!/usr/bin/env python3
"""
Sponge - AI Root Cause Analysis Tool with Performance Monitoring
Machine Learning-powered log analysis, performance monitoring, and error resolution.

Features:
- Integration with CloudWatch, DataDog, Dynatrace, Splunk, and more
- CPU, Memory, Latency, and Zombie process analysis
- ML-powered error clustering
- Detailed implementation steps for fixes
- Knowledge base for resolution tracking
"""

import sys
import argparse
import logging
from logging.config import dictConfig
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Core imports
from src.ml_engine import LogRCAEngine
from src.scraper import SolutionScraper
from src.storage import KnowledgeBase
from src.config import LOGGING_CONFIG, LOG_SOURCE, LOG_FILE_PATH
from src import __version__

# Performance analyzers
from src.analyzers.performance_engine import PerformanceAnalysisEngine

# Integration imports
from src.integrations.base import LogEntry
from src.integrations.aws_cloudwatch import CloudWatchIntegration
from src.integrations.datadog import DataDogIntegration
from src.integrations.dynatrace import DynatraceIntegration

# Configure logging
dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def print_banner():
    """Print enhanced application banner."""
    banner = f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🧽 SPONGE - AI Root Cause Analysis & Performance Monitor       ║
║   Version {__version__}                                                   ║
║                                                                   ║
║   ML-Powered Log Analysis + Performance Monitoring               ║
║   Integrated with: CloudWatch, DataDog, Dynatrace, Splunk+       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_separator(char="─", length=70):
    """Print a separator line."""
    print(char * length)


def fetch_mock_logs():
    """Generate comprehensive mock log data for testing."""
    return [
        # Connection errors
        "CRITICAL: ConnectionRefusedError: [Errno 111] Connection refused at 10.0.1.5",
        "CRITICAL: ConnectionRefusedError: [Errno 111] Connection refused at 10.0.1.6",
        "CRITICAL: ConnectionRefusedError: [Errno 111] Connection refused at 192.168.1.10",

        # Value errors
        "ERROR: ValueError: invalid literal for int() with base 10: 'xyz'",
        "ERROR: ValueError: invalid literal for int() with base 10: 'abc'",

        # NullPointer errors
        "ERROR: NullPointerException in module AuthService at line 245",
        "ERROR: NullPointerException in module AuthService at line 247",

        # Database issues
        "WARNING: Database query timeout after 30 seconds on connection pool-5",
        "WARNING: Database query timeout after 30 seconds on connection pool-8",

        # File errors
        "ERROR: FileNotFoundException: config.yml not found at /etc/app/",
        "ERROR: FileNotFoundException: settings.json not found at /opt/config/",

        # Memory errors
        "CRITICAL: OutOfMemoryError: Java heap space exceeded at 0x7f8a3c00",
        "CRITICAL: OutOfMemoryError: Java heap space exceeded at 0x7f8a4d11",

        # HTTP errors
        "ERROR: HTTP 500 Internal Server Error at endpoint /api/users",
        "ERROR: HTTP 500 Internal Server Error at endpoint /api/products",

        # Performance issues
        "WARNING: High CPU usage: 95% on host server-01",
        "WARNING: High memory usage: 87% on host server-02",
        "ERROR: Request timeout after 5000ms to service payment-service",

        # Zombie/resource issues
        "ERROR: Too many open files (EMFILE) in process 1234",
        "WARNING: Thread pool exhausted: 200/200 threads in use",
        "ERROR: Connection pool exhausted: no connections available",

        # Info logs
        "INFO: System is running normally",
        "INFO: User login successful for user_id 12345",
    ]


def fetch_logs_from_file(file_path: str):
    """Read logs from a text file."""
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Log file not found: {file_path}")
            return []

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            logs = [line.strip() for line in f if line.strip()]

        logger.info(f"Loaded {len(logs)} logs from {file_path}")
        return logs

    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return []


def analyze_performance(args, kb: KnowledgeBase):
    """Run comprehensive performance analysis."""
    print("\n🔍 Performance Analysis Mode")
    print_separator()

    # Initialize performance engine
    perf_engine = PerformanceAnalysisEngine()

    # Determine integration
    integration_type = args.integration

    if integration_type == 'mock':
        print("⚠️  Using mock data (no real integration)")
        # Create mock metrics and logs for demonstration
        from src.integrations.base import PerformanceMetric

        # Mock performance metrics showing issues
        mock_metrics = [
            PerformanceMetric("cpu.usage", 85.0, "percent", datetime.utcnow(), {"host": "server-01"}),
            PerformanceMetric("cpu.usage", 90.0, "percent", datetime.utcnow(), {"host": "server-01"}),
            PerformanceMetric("cpu.usage", 88.0, "percent", datetime.utcnow(), {"host": "server-01"}),
            PerformanceMetric("memory.used", 7.5, "GB", datetime.utcnow(), {"host": "server-01"}),
            PerformanceMetric("memory.used", 7.8, "GB", datetime.utcnow(), {"host": "server-01"}),
            PerformanceMetric("latency", 1500, "ms", datetime.utcnow(), {"endpoint": "/api/users"}),
            PerformanceMetric("latency", 1800, "ms", datetime.utcnow(), {"endpoint": "/api/users"}),
        ]

        # Convert mock logs to LogEntry objects
        mock_log_strings = fetch_mock_logs()
        mock_log_entries = [
            LogEntry(
                timestamp=datetime.utcnow(),
                message=log,
                level="ERROR" if "ERROR" in log else "WARNING" if "WARNING" in log else "INFO",
                source="mock",
                metadata={}
            )
            for log in mock_log_strings
        ]

        report = perf_engine.analyze_from_data(mock_log_entries, mock_metrics)

    else:
        print(f"📡 Connecting to {integration_type}...")
        # Real integration
        integration_config = {
            'aws_access_key_id': args.aws_key,
            'aws_secret_access_key': args.aws_secret,
            'aws_region': args.aws_region,
            'log_group_name': args.log_group
        } if integration_type == 'cloudwatch' else {}

        try:
            if integration_type == 'cloudwatch':
                integration = CloudWatchIntegration(integration_config)
            elif integration_type == 'datadog':
                integration = DataDogIntegration({
                    'api_key': args.datadog_api_key,
                    'app_key': args.datadog_app_key
                })
            elif integration_type == 'dynatrace':
                integration = DynatraceIntegration({
                    'api_token': args.dynatrace_token,
                    'environment_url': args.dynatrace_url
                })
            else:
                print(f"❌ Integration '{integration_type}' not fully implemented yet")
                return

            print(f"✅ Connected to {integration_type}")
            report = perf_engine.analyze_from_integration(integration, hours=args.hours)

        except Exception as e:
            logger.error(f"Integration failed: {e}")
            print(f"❌ Failed to connect to {integration_type}: {e}")
            return

    # Display results
    print_separator()
    print(f"\n📊 Performance Analysis Results")
    print_separator()

    summary = report.get_summary()
    print(f"Total Issues Found: {summary['total_issues']}")
    print(f"  - CPU Issues: {summary['cpu_issues']}")
    print(f"  - Memory Issues: {summary['memory_issues']}")
    print(f"  - Latency Issues: {summary['latency_issues']}")
    print(f"  - Zombie Detections: {summary['zombie_detections']}")
    print(f"  - Error Logs: {summary['error_logs']}")

    print(f"\nSeverity Breakdown:")
    for severity, count in summary['severity_breakdown'].items():
        if count > 0:
            print(f"  - {severity.upper()}: {count}")

    # Save issues to knowledge base
    scraper = SolutionScraper()
    saved_count = 0

    all_issues = report.get_all_issues()

    for issue in all_issues:
        category = issue.get('category', 'Unknown')
        issue_type = issue.get('issue_type', 'unknown')
        severity = issue.get('severity', 'medium')
        description = issue.get('description', '')
        recommendations = issue.get('recommendations', [])

        print(f"\n🔴 {category} Issue: {description}")

        # Get detailed solution
        solution = scraper.find_solution(description)

        # Save to knowledge base
        kb.save_entry(
            error=description,
            fix=solution['solution'],
            source=solution['source'],
            count=1,
            confidence=solution.get('confidence', 'medium'),
            category=category,
            issue_type=issue_type,
            severity=severity,
            implementation_steps=solution.get('implementation_steps', []),
            recommendations=recommendations
        )
        saved_count += 1

        print(f"   💡 Solution: {solution['solution'][:150]}...")
        print(f"   🔗 Source: {solution['source']}")
        print(f"   📋 Implementation Steps: {len(solution.get('implementation_steps', []))} steps")

    print_separator()
    print(f"\n✅ Analysis Complete!")
    print(f"   📁 Saved {saved_count} issues to knowledge base")
    print(f"   📊 Knowledge base: {kb.filename}")
    print_separator()


def analyze_errors(args, kb: KnowledgeBase):
    """Run error pattern analysis (original functionality)."""
    print("\n🔍 Error Pattern Analysis Mode")
    print_separator()

    # Initialize components
    print("[1/5] Initializing ML Engine...")
    engine = LogRCAEngine()

    print("[2/5] Initializing Web Scraper...")
    scraper = SolutionScraper()

    # Fetch logs
    print(f"[3/5] Fetching logs from source: {args.source}")

    if args.source == 'file':
        if not args.file:
            print("❌ Error: Please specify --file when using --source=file")
            return 1

        logs = fetch_logs_from_file(args.file)
    else:
        logs = fetch_mock_logs()

    if not logs:
        print("❌ No logs found to analyze!")
        return 1

    print(f"   ✓ Ingested {len(logs)} log entries")

    # Analyze (RCA)
    print("[4/5] Running TensorFlow Root Cause Analysis...")

    try:
        root_causes = engine.analyze_root_causes(logs)
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"❌ Analysis failed: {e}")
        return 1

    if not root_causes:
        print("   ℹ️  No significant error patterns found.")
        print("\n✅ Analysis complete - no errors detected!")
        return 0

    print(f"   ✓ Identified {len(root_causes)} unique error patterns")

    # Resolve and Save
    print(f"[5/5] Finding solutions and updating knowledge base...")
    print_separator()

    for i, rc in enumerate(root_causes, 1):
        error_pattern = rc['representative_log']
        count = rc['count']

        print(f"\n🔴 Error Pattern #{i} (Occurrences: {count})")
        print(f"   Pattern: {error_pattern}")

        # Check cache first
        resolution = kb.check_cache(error_pattern)

        if resolution:
            print(f"   💾 [Cache Hit] Found existing solution")
            print(f"      Confidence: {resolution.get('confidence', 'unknown')}")
        else:
            print(f"   🌐 [Cache Miss] Searching web for solution...")

            try:
                resolution = scraper.find_solution(error_pattern)
                # Save to knowledge base with implementation steps
                kb.save_entry(
                    error_pattern,
                    resolution['solution'],
                    resolution['source'],
                    count,
                    resolution.get('confidence', 'medium'),
                    category='Error',
                    issue_type='error_pattern',
                    severity='high',
                    implementation_steps=resolution.get('implementation_steps', []),
                    recommendations=[]
                )
                print(f"      Confidence: {resolution.get('confidence', 'unknown')}")
            except Exception as e:
                logger.error(f"Error during web scraping: {e}")
                resolution = {
                    "solution": f"Error retrieving solution: {e}",
                    "source": "Error",
                    "confidence": "low"
                }

        # Display solution
        solution_text = resolution['solution']
        if len(solution_text) > 200:
            solution_text = solution_text[:200] + "..."

        print(f"   💡 Solution: {solution_text}")
        print(f"   🔗 Source: {resolution['source']}")

        # Display implementation steps if available
        steps = resolution.get('implementation_steps', [])
        if steps:
            print(f"   📋 Implementation Steps ({len(steps)}):")
            for idx, step in enumerate(steps[:3], 1):  # Show first 3
                print(f"      {idx}. {step[:80]}...")

    # Summary
    print_separator()
    print("\n✅ Analysis Complete!")
    print(f"   📁 Results saved to: {kb.filename}")
    print(f"   📊 Processed {len(logs)} logs")
    print(f"   🎯 Found {len(root_causes)} error patterns")
    print_separator()

    return 0


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Sponge - AI RCA & Performance Monitoring Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Mode selection
    parser.add_argument(
        '--mode',
        choices=['errors', 'performance', 'stats', 'export', 'top'],
        default='errors',
        help='Analysis mode (default: errors)'
    )

    # Data source
    parser.add_argument(
        '--source',
        choices=['mock', 'file'],
        default='mock',
        help='Log source type (default: mock)'
    )

    parser.add_argument(
        '--file',
        type=str,
        help='Path to log file (required if --source=file)'
    )

    # Integration options
    parser.add_argument(
        '--integration',
        choices=['mock', 'cloudwatch', 'datadog', 'dynatrace', 'splunk'],
        default='mock',
        help='Monitoring platform integration (default: mock)'
    )

    parser.add_argument('--hours', type=int, default=24, help='Hours of data to analyze')

    # CloudWatch options
    parser.add_argument('--aws-key', help='AWS access key')
    parser.add_argument('--aws-secret', help='AWS secret key')
    parser.add_argument('--aws-region', default='us-east-1', help='AWS region')
    parser.add_argument('--log-group', help='CloudWatch log group name')

    # DataDog options
    parser.add_argument('--datadog-api-key', help='DataDog API key')
    parser.add_argument('--datadog-app-key', help='DataDog app key')

    # Dynatrace options
    parser.add_argument('--dynatrace-token', help='Dynatrace API token')
    parser.add_argument('--dynatrace-url', help='Dynatrace environment URL')

    # Other options
    parser.add_argument('--stats', action='store_true', help='Show KB statistics')
    parser.add_argument('--export', type=str, metavar='PATH', help='Export KB to CSV')
    parser.add_argument('--top', type=int, metavar='N', help='Show top N errors')
    parser.add_argument('--version', action='version', version=f'Sponge v{__version__}')

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Initialize knowledge base
    kb = KnowledgeBase()

    # Handle different modes
    if args.stats or args.mode == 'stats':
        print("📊 Knowledge Base Statistics")
        print_separator()
        stats = kb.get_statistics()
        print(f"Total Error Patterns: {stats.get('total_patterns', 0)}")
        print(f"Total Occurrences: {stats.get('total_occurrences', 0)}")
        print(f"Average Frequency: {stats.get('avg_frequency', 0):.2f}")
        print(f"High Confidence: {stats.get('high_confidence_count', 0)}")
        print(f"Medium Confidence: {stats.get('medium_confidence_count', 0)}")
        print(f"Low Confidence: {stats.get('low_confidence_count', 0)}")
        print_separator()
        return 0

    if args.export or args.mode == 'export':
        export_path = args.export if args.export else 'knowledge_base_export.csv'
        print(f"📤 Exporting knowledge base to: {export_path}")
        if kb.export_to_csv(export_path):
            print("✅ Export successful!")
        else:
            print("❌ Export failed!")
        return 0

    if args.top or args.mode == 'top':
        limit = args.top if args.top else 10
        print(f"🔝 Top {limit} Errors")
        print_separator()
        top_errors = kb.get_top_errors(limit=limit)

        if not top_errors:
            print("No errors found in knowledge base.")
        else:
            for i, error in enumerate(top_errors, 1):
                print(f"\n{i}. Error Pattern (Frequency: {error['frequency']})")
                print(f"   {error['error_pattern']}")
                print(f"   Solution: {error['solution'][:100]}...")
                print(f"   Confidence: {error['confidence']}")

        print_separator()
        return 0

    # Main analysis modes
    if args.mode == 'performance':
        analyze_performance(args, kb)
    else:  # errors mode (default)
        return analyze_errors(args, kb)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
