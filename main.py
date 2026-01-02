#!/usr/bin/env python3
"""
Sponge - AI Root Cause Analysis Tool
Machine Learning-powered log analysis with TensorFlow and web scraping.

Usage:
    python main.py [--source SOURCE] [--file FILE] [--stats] [--export]
"""

import sys
import argparse
import logging
from logging.config import dictConfig
from pathlib import Path

from src.ml_engine import LogRCAEngine
from src.scraper import SolutionScraper
from src.storage import KnowledgeBase
from src.config import LOGGING_CONFIG, LOG_SOURCE, LOG_FILE_PATH
from src import __version__

# Configure logging
dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def fetch_mock_logs():
    """
    Generate mock log data for testing and demonstration.

    Returns:
        List of sample log messages
    """
    return [
        "CRITICAL: ConnectionRefusedError: [Errno 111] Connection refused at 10.0.1.5",
        "CRITICAL: ConnectionRefusedError: [Errno 111] Connection refused at 10.0.1.6",
        "CRITICAL: ConnectionRefusedError: [Errno 111] Connection refused at 10.0.1.9",
        "CRITICAL: ConnectionRefusedError: [Errno 111] Connection refused at 192.168.1.10",
        "ERROR: ValueError: invalid literal for int() with base 10: 'xyz'",
        "ERROR: ValueError: invalid literal for int() with base 10: 'abc'",
        "ERROR: ValueError: invalid literal for int() with base 10: '123abc'",
        "ERROR: NullPointerException in module AuthService at line 245",
        "ERROR: NullPointerException in module AuthService at line 247",
        "WARNING: Database query timeout after 30 seconds on connection pool-5",
        "WARNING: Database query timeout after 30 seconds on connection pool-8",
        "INFO: System is running normally",
        "INFO: User login successful for user_id 12345",
        "INFO: User login successful for user_id 67890",
        "ERROR: FileNotFoundException: config.yml not found at /etc/app/",
        "ERROR: FileNotFoundException: settings.json not found at /opt/config/",
        "CRITICAL: OutOfMemoryError: Java heap space exceeded at 0x7f8a3c00",
        "CRITICAL: OutOfMemoryError: Java heap space exceeded at 0x7f8a4d11",
    ]


def fetch_logs_from_file(file_path: str):
    """
    Read logs from a text file.

    Args:
        file_path: Path to log file

    Returns:
        List of log lines
    """
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


def print_banner():
    """Print application banner."""
    banner = f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🧽 SPONGE - AI Root Cause Analysis Tool                        ║
║   Version {__version__}                                                   ║
║                                                                   ║
║   Machine Learning-Powered Log Analysis & Error Resolution       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_separator(char="─", length=70):
    """Print a separator line."""
    print(char * length)


def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Sponge - AI Root Cause Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

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

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show knowledge base statistics and exit'
    )

    parser.add_argument(
        '--export',
        type=str,
        metavar='PATH',
        help='Export knowledge base to CSV file'
    )

    parser.add_argument(
        '--top',
        type=int,
        metavar='N',
        help='Show top N errors from knowledge base and exit'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'Sponge v{__version__}'
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Initialize knowledge base
    kb = KnowledgeBase()

    # Handle statistics mode
    if args.stats:
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

    # Handle export mode
    if args.export:
        print(f"📤 Exporting knowledge base to: {args.export}")
        if kb.export_to_csv(args.export):
            print("✅ Export successful!")
        else:
            print("❌ Export failed!")
        return 0

    # Handle top errors mode
    if args.top:
        print(f"🔝 Top {args.top} Errors")
        print_separator()
        top_errors = kb.get_top_errors(limit=args.top)

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

    # Main analysis mode
    print("🔍 Starting Root Cause Analysis")
    print_separator()

    # 1. Initialize components
    print("[1/5] Initializing ML Engine...")
    engine = LogRCAEngine()

    print("[2/5] Initializing Web Scraper...")
    scraper = SolutionScraper()

    # 2. Fetch logs
    print(f"[3/5] Fetching logs from source: {args.source}")

    if args.source == 'file':
        if not args.file:
            logger.error("--file argument required when --source=file")
            print("❌ Error: Please specify --file when using --source=file")
            return 1

        logs = fetch_logs_from_file(args.file)
    else:
        logs = fetch_mock_logs()

    if not logs:
        print("❌ No logs found to analyze!")
        return 1

    print(f"   ✓ Ingested {len(logs)} log entries")

    # 3. Analyze (RCA)
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

    # 4. Resolve and Save
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
                # Save to knowledge base
                kb.save_entry(
                    error_pattern,
                    resolution['solution'],
                    resolution['source'],
                    count,
                    resolution.get('confidence', 'medium')
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

    # Summary
    print_separator()
    print("\n✅ Analysis Complete!")
    print(f"   📁 Results saved to: {kb.filename}")
    print(f"   📊 Processed {len(logs)} logs")
    print(f"   🎯 Found {len(root_causes)} error patterns")
    print_separator()

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
