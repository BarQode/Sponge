#!/usr/bin/env python3
"""
Sponge RCA Tool - Local Application Runner

Main entry point for running Sponge as a local application on Mac/Windows/Linux.
Supports multiple operation modes for different use cases.
"""

import sys
import argparse
import logging
from pathlib import Path
import time
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import Config
from src.ml_engine import HybridMLEngine
from src.scraper import Scraper
from src.storage import StorageManager
from src.knowledge_base import EnhancedKnowledgeBase

# SRE Automation
from src.sre_automation import (
    ToilTracker,
    RunbookEngine,
    RunbookExecutor,
    SLOManager,
    SelfHealingSystem,
    create_common_runbooks,
    create_common_slos
)

# Security Automation
from src.security_automation import (
    JITAccessManager,
    SOAREngine,
    ComplianceScanner,
    ThreatIntelligence
)

# SOAP Integration
from src.soap_integration import run_soap_server

# Prometheus
from src.prometheus_integration import get_metrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SpongeApplication:
    """
    Main Sponge Application

    Runs all components in an integrated fashion for local operation.
    """

    def __init__(self, config_path: str = None):
        logger.info("Initializing Sponge RCA Tool...")

        self.config = Config(config_path) if config_path else Config()

        # Core components
        self.storage = StorageManager()
        self.knowledge_base = EnhancedKnowledgeBase()
        self.ml_engine = HybridMLEngine()
        self.scraper = Scraper()

        # SRE components
        self.toil_tracker = ToilTracker()
        self.runbook_engine = RunbookEngine()
        self.runbook_executor = RunbookExecutor(self.runbook_engine)
        self.slo_manager = SLOManager()

        # Security components
        self.jit_access = JITAccessManager()
        self.soar_engine = SOAREngine()
        self.compliance_scanner = ComplianceScanner()
        self.threat_intel = ThreatIntelligence()

        # Self-healing (integrates SRE components)
        self.self_healing = SelfHealingSystem(
            self.slo_manager,
            self.runbook_engine,
            self.toil_tracker
        )

        # Metrics
        self.metrics = get_metrics()

        # Initialize common runbooks and SLOs
        create_common_runbooks(self.runbook_engine)
        create_common_slos(self.slo_manager)

        logger.info("Sponge RCA Tool initialized successfully")

    def run_cli_mode(self):
        """Run in interactive CLI mode"""
        logger.info("Starting CLI mode...")

        print("\n" + "="*60)
        print("  Sponge RCA Tool - Interactive CLI")
        print("="*60)
        print("\nAvailable commands:")
        print("  1. Train ML model")
        print("  2. Scrape data from URL")
        print("  3. Query knowledge base")
        print("  4. Track toil task")
        print("  5. Execute runbook")
        print("  6. Check SLO status")
        print("  7. Request JIT access")
        print("  8. Scan compliance")
        print("  9. Check threat intelligence")
        print("  0. Exit")

        while True:
            try:
                choice = input("\nEnter command number: ").strip()

                if choice == "0":
                    print("Goodbye!")
                    break
                elif choice == "1":
                    self._train_model_interactive()
                elif choice == "2":
                    self._scrape_data_interactive()
                elif choice == "3":
                    self._query_kb_interactive()
                elif choice == "4":
                    self._track_toil_interactive()
                elif choice == "5":
                    self._execute_runbook_interactive()
                elif choice == "6":
                    self._check_slo_interactive()
                elif choice == "7":
                    self._request_access_interactive()
                elif choice == "8":
                    self._scan_compliance_interactive()
                elif choice == "9":
                    self._check_threat_interactive()
                else:
                    print("Invalid choice. Please try again.")

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"Error: {e}")

    def run_monitoring_mode(self):
        """Run in continuous monitoring mode"""
        logger.info("Starting monitoring mode...")

        # Start Prometheus metrics server
        self.metrics.start_server_async()
        logger.info("Prometheus metrics available at http://localhost:9090")

        # Continuous monitoring loop
        try:
            while True:
                logger.info("Running monitoring cycle...")

                # Check SLOs and auto-heal
                actions = self.self_healing.monitor_and_heal()
                if actions:
                    logger.info(f"Took {len(actions)} self-healing actions")

                # Revoke expired access grants
                revoked = self.jit_access.revoke_expired_grants()
                if revoked > 0:
                    logger.info(f"Auto-revoked {revoked} expired access grants")

                # Update system metrics
                import psutil
                cpu = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory().percent
                disk = {"/": psutil.disk_usage("/").percent}
                self.metrics.update_system_metrics(cpu, memory, disk)

                # Sleep for monitoring interval
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")

    def run_soap_mode(self):
        """Run SOAP API server"""
        logger.info("Starting SOAP API server...")
        run_soap_server(host="0.0.0.0", port=8001)

    def run_training_mode(self, data_source: str = None):
        """Run ML training mode"""
        logger.info("Starting ML training mode...")

        if data_source:
            logger.info(f"Importing data from {data_source}")
            # Import data logic here

        # Train model
        logger.info("Training ML model...")
        start_time = time.time()

        try:
            # Placeholder for actual training
            self.ml_engine.train([], [])

            duration = time.time() - start_time
            logger.info(f"Training completed in {duration:.2f} seconds")

            self.metrics.record_ml_training("rca_model", duration, True)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Training failed: {e}")
            self.metrics.record_ml_training("rca_model", duration, False)

    # Interactive mode helpers

    def _train_model_interactive(self):
        """Interactive ML training"""
        print("\n--- ML Model Training ---")
        print("Training RCA model...")
        self.run_training_mode()

    def _scrape_data_interactive(self):
        """Interactive data scraping"""
        print("\n--- Data Scraping ---")
        url = input("Enter URL to scrape: ").strip()
        if url:
            try:
                result = self.scraper.scrape(url)
                print(f"Scraped successfully: {len(result.get('content', ''))} characters")
                self.metrics.record_scraping_operation(url, True)
            except Exception as e:
                print(f"Scraping failed: {e}")
                self.metrics.record_scraping_operation(url, False)

    def _query_kb_interactive(self):
        """Interactive knowledge base query"""
        print("\n--- Knowledge Base Query ---")
        query = input("Enter search query: ").strip()
        if query:
            results = self.knowledge_base.search({'query': query})
            print(f"Found {len(results)} results")
            for i, result in enumerate(results[:5], 1):
                print(f"{i}. {result.get('error_pattern', 'N/A')}")

    def _track_toil_interactive(self):
        """Interactive toil tracking"""
        print("\n--- Track Toil Task ---")
        task_id = input("Task ID: ").strip()
        title = input("Title: ").strip()
        category = input("Category (provisioning/restart/deployment): ").strip()
        time_spent = float(input("Time spent (hours): ").strip() or "0")

        if task_id and title:
            self.toil_tracker.track_task(
                task_id=task_id,
                title=title,
                category=category,
                time_spent=time_spent,
                is_manual=True,
                is_repetitive=True,
                is_automatable=True
            )
            print("Task tracked successfully!")
            self.metrics.record_toil_task(category, time_spent, True)

    def _execute_runbook_interactive(self):
        """Interactive runbook execution"""
        print("\n--- Execute Runbook ---")
        print("Available runbooks:")
        for i, name in enumerate(self.runbook_engine.list_runbooks(), 1):
            print(f"{i}. {name}")

        runbook_name = input("\nEnter runbook name: ").strip()
        if runbook_name:
            start_time = time.time()
            result = self.runbook_executor.execute(runbook_name)
            duration = time.time() - start_time

            print(f"\nResult: {'Success' if result.success else 'Failed'}")
            print(f"Steps executed: {result.steps_executed}")
            print(f"Execution time: {result.execution_time:.2f}s")

            self.metrics.record_runbook_execution(runbook_name, duration, result.success)

    def _check_slo_interactive(self):
        """Interactive SLO checking"""
        print("\n--- SLO Status ---")
        for slo_name in self.slo_manager.slos.keys():
            error_budget = self.slo_manager.calculate_error_budget(slo_name)
            if error_budget:
                print(f"\n{slo_name}:")
                print(f"  Status: {error_budget.status}")
                print(f"  Remaining budget: {error_budget.remaining:.2f}")
                print(f"  Burn rate: {error_budget.burn_rate:.2f}")

    def _request_access_interactive(self):
        """Interactive access request"""
        print("\n--- Request JIT Access ---")
        requester = input("Your username: ").strip()
        resource = input("Resource (prod-db/staging-db/prod-admin): ").strip()
        permission = input("Permission level (read/write/admin): ").strip()
        duration = int(input("Duration (minutes): ").strip() or "60")
        reason = input("Reason: ").strip()

        if all([requester, resource, permission, reason]):
            request = self.jit_access.request_access(
                requester=requester,
                resource=resource,
                permission_level=permission,
                duration_minutes=duration,
                reason=reason
            )
            if request:
                print(f"\nRequest created: {request.request_id}")
                print(f"Status: {request.status}")
                self.metrics.record_access_request(resource, request.status)

    def _scan_compliance_interactive(self):
        """Interactive compliance scanning"""
        print("\n--- Compliance Scan ---")
        print("Scanning AWS resources for compliance...")

        try:
            violations = self.compliance_scanner.scan_all_policies()
            print(f"\nFound {len(violations)} violations")

            for v in violations[:5]:
                print(f"  [{v.severity.value}] {v.policy_id}: {v.resource_id}")

        except Exception as e:
            print(f"Scan failed: {e}")

    def _check_threat_interactive(self):
        """Interactive threat intelligence check"""
        print("\n--- Threat Intelligence ---")
        ip = input("Enter IP address to check: ").strip()

        if ip:
            try:
                reputation = self.threat_intel.check_ip_reputation(ip)
                if reputation:
                    print(f"\nIP: {reputation.ip}")
                    print(f"Reputation Score: {reputation.reputation_score}/100")
                    print(f"Malicious: {reputation.is_malicious}")
                    print(f"Country: {reputation.country}")
                    print(f"Reports: {reputation.reports}")

                    self.metrics.record_threat_lookup('ip', reputation.is_malicious)
                else:
                    print("No threat data found")
            except Exception as e:
                print(f"Lookup failed: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Sponge RCA Tool - Root Cause Analysis with SRE & Security Automation"
    )

    parser.add_argument(
        "--mode",
        choices=["cli", "monitor", "soap", "training"],
        default="cli",
        help="Operation mode (default: cli)"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )

    parser.add_argument(
        "--data-source",
        type=str,
        help="Data source for training mode"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9090,
        help="Prometheus metrics port (default: 9090)"
    )

    args = parser.parse_args()

    # Create and run application
    try:
        app = SpongeApplication(config_path=args.config)

        if args.mode == "cli":
            app.run_cli_mode()
        elif args.mode == "monitor":
            app.run_monitoring_mode()
        elif args.mode == "soap":
            app.run_soap_mode()
        elif args.mode == "training":
            app.run_training_mode(data_source=args.data_source)

    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
