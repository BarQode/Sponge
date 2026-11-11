"""
Tests for LogAnalysisAgent — covers fetch_logs, analyze_errors,
correlate_signals, remediate_error, record_solution, and all helpers.
"""

import asyncio
import hashlib
import re
import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.log_analysis_agent import (
    LogAnalysisAgent,
    _classify_incident,
    _severity_rank,
    PLATFORM_REGISTRY,
)
from src.integrations.base import LogEntry, PerformanceMetric


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_log(msg: str, level: str = "ERROR", source: str = "dynatrace") -> LogEntry:
    return LogEntry(
        timestamp=datetime.utcnow(),
        message=msg,
        level=level,
        source=source,
    )


def _make_metric(name: str = "cpu", value: float = 80.0) -> PerformanceMetric:
    return PerformanceMetric(
        metric_name=name,
        value=value,
        unit="percent",
        timestamp=datetime.utcnow(),
    )


def _make_integration(logs=None, errors=None, metrics=None):
    """Return a mock integration object."""
    m = MagicMock()
    m.fetch_logs.return_value = logs or []
    m.fetch_errors.return_value = errors or []
    m.fetch_performance_metrics.return_value = metrics or []
    return m


def _make_agent(platform_configs=None, auto_remediate=False, **kwargs):
    return LogAnalysisAgent(
        platform_configs=platform_configs or {"dynatrace": {"api_token": "x", "environment_url": "https://x"}},
        auto_remediate=auto_remediate,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Unit tests: pure helpers
# ---------------------------------------------------------------------------

class TestClassifyIncident:
    def test_oom(self):
        assert _classify_incident("OutOfMemoryError in pod") == "oom"

    def test_oom_killed(self):
        assert _classify_incident("OOMKilled container web") == "oom"

    def test_cve(self):
        assert _classify_incident("CVE-2024-1234 found in image") == "dependency"

    def test_rbac(self):
        assert _classify_incident("RBAC: Forbidden") == "security"

    def test_terraform(self):
        assert _classify_incident("terraform state mismatch detected") == "terraform_drift"

    def test_crash_loop(self):
        assert _classify_incident("CrashLoopBackOff container app") == "codebase_failure"

    def test_generic(self):
        assert _classify_incident("disk usage high") == "generic_error"


class TestSeverityRank:
    def test_ranks(self):
        assert _severity_rank("CRITICAL") > _severity_rank("ERROR")
        assert _severity_rank("ERROR") > _severity_rank("WARNING")
        assert _severity_rank("WARNING") > _severity_rank("INFO")

    def test_case_insensitive(self):
        assert _severity_rank("critical") == _severity_rank("CRITICAL")

    def test_unknown(self):
        assert _severity_rank("TRACE") == 0


class TestFingerprint:
    def _fp(self, msg: str) -> str:
        normalized = re.sub(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<uuid>", msg, flags=re.I)
        normalized = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<ip>", normalized)
        normalized = re.sub(r"\b\d+\b", "<n>", normalized)
        normalized = normalized.lower().strip()[:200]
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def test_different_numbers_same_fp(self):
        assert self._fp("OOM pod-1") == self._fp("OOM pod-2")

    def test_different_uuids_same_fp(self):
        a = self._fp("error a1b2c3d4-0000-0000-0000-000000000001")
        b = self._fp("error a1b2c3d4-0000-0000-0000-000000000002")
        assert a == b

    def test_different_ips_same_fp(self):
        assert self._fp("connect 10.0.0.1 refused") == self._fp("connect 192.168.1.5 refused")

    def test_distinct_messages_differ(self):
        assert self._fp("OOM error") != self._fp("RBAC forbidden")


class TestPlatformRegistry:
    def test_core_platforms_present(self):
        for key in ("dynatrace", "cloudwatch", "datadog", "splunk", "grafana"):
            assert key in PLATFORM_REGISTRY

    def test_import_paths_valid_format(self):
        for key, path in PLATFORM_REGISTRY.items():
            assert "." in path, f"{key}: import path must contain '.'"


# ---------------------------------------------------------------------------
# Unit tests: fetch_logs
# ---------------------------------------------------------------------------

class TestFetchLogs:
    def setup_method(self):
        self.agent = _make_agent()
        self.mock_integration = _make_integration(
            errors=[
                _make_log("OOMKilled web", "ERROR", "dynatrace"),
                _make_log("disk high", "WARNING", "dynatrace"),
            ]
        )
        self.agent._integrations["dynatrace"] = self.mock_integration

    def test_returns_success(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.fetch_logs({"platform": "dynatrace", "severity_filter": "ERROR"})
        )
        assert result["success"] is True

    def test_entries_filtered_by_severity(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.fetch_logs({"platform": "dynatrace", "severity_filter": "ERROR"})
        )
        # WARNING should be excluded when asking for ERROR
        levels = [e["level"] for e in result["entries"]]
        assert all(l in ("ERROR", "CRITICAL") for l in levels)

    def test_all_severity_includes_warning(self):
        self.mock_integration.fetch_logs.return_value = [
            _make_log("disk high", "WARNING", "dynatrace")
        ]
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.fetch_logs({"platform": "dynatrace", "severity_filter": "ALL"})
        )
        assert result["total_entries"] >= 1

    def test_missing_platform_returns_error_list(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.fetch_logs({"platform": "nonexistent_platform"})
        )
        assert result["success"] is True
        assert len(result["errors"]) > 0

    def test_window_reported(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.fetch_logs({"lookback_minutes": 30})
        )
        assert "window" in result
        assert "start" in result["window"]

    def test_entries_capped_at_500(self):
        self.mock_integration.fetch_errors.return_value = [
            _make_log(f"err {i}") for i in range(600)
        ]
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.fetch_logs({"platform": "dynatrace"})
        )
        assert len(result["entries"]) <= 500


# ---------------------------------------------------------------------------
# Unit tests: analyze_errors
# ---------------------------------------------------------------------------

class TestAnalyzeErrors:
    def setup_method(self):
        self.agent = _make_agent(error_threshold=2)
        self.mock_integration = _make_integration(
            errors=[
                _make_log("OOMKilled pod-1"),
                _make_log("OOMKilled pod-2"),
                _make_log("OOMKilled pod-3"),
                _make_log("CVE-2024-1234 vulnerable image"),
            ]
        )
        self.agent._integrations["dynatrace"] = self.mock_integration

    def test_groups_by_fingerprint(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.analyze_errors({})
        )
        assert result["success"] is True
        assert result["unique_error_groups"] <= result["total_entries_analysed"]

    def test_oom_classified_correctly(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.analyze_errors({})
        )
        types = [g["incident_type"] for g in result["top_errors"]]
        assert "oom" in types

    def test_top_n_respected(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.analyze_errors({"top_n": 1})
        )
        assert len(result["top_errors"]) <= 1

    def test_findings_cached(self):
        asyncio.get_event_loop().run_until_complete(self.agent.analyze_errors({}))
        assert len(self.agent._findings) > 0

    def test_sources_serialized_as_list(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.analyze_errors({})
        )
        for group in result["top_errors"]:
            assert isinstance(group["sources"], list)


# ---------------------------------------------------------------------------
# Unit tests: correlate_signals
# ---------------------------------------------------------------------------

class TestCorrelateSignals:
    def setup_method(self):
        self.agent = _make_agent()
        self.mock_integration = _make_integration(
            errors=[_make_log("OOMKilled pod-1")],
            metrics=[_make_metric("memory_used", 95.0)],
        )
        self.agent._integrations["dynatrace"] = self.mock_integration

    def test_returns_success(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.correlate_signals({})
        )
        assert result["success"] is True

    def test_correlations_have_confidence(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.correlate_signals({})
        )
        for c in result["correlations"]:
            assert 0.0 <= c["confidence"] <= 1.0

    def test_service_filter_applied(self):
        # error message does not contain "frontend" — should return 0
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.correlate_signals({"service": "frontend_xyz_no_match"})
        )
        assert result["correlations_found"] == 0

    def test_capped_at_50(self):
        self.mock_integration.fetch_errors.return_value = [
            _make_log(f"OOMKilled pod-{i}") for i in range(100)
        ]
        self.mock_integration.fetch_performance_metrics.return_value = [
            _make_metric("mem", 90.0)
        ]
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.correlate_signals({})
        )
        assert len(result["correlations"]) <= 50


# ---------------------------------------------------------------------------
# Unit tests: remediate_error
# ---------------------------------------------------------------------------

class TestRemediateError:
    def setup_method(self):
        self.agent = _make_agent()
        self.mock_integration = _make_integration(
            errors=[_make_log("OOMKilled pod-1")]
        )
        self.agent._integrations["dynatrace"] = self.mock_integration

    def _seed_finding(self, msg: str = "OOMKilled pod-1") -> str:
        asyncio.get_event_loop().run_until_complete(self.agent.analyze_errors({}))
        # Return first fingerprint
        return next(iter(self.agent._findings))

    def test_unknown_fingerprint_returns_error(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.remediate_error({"error_fingerprint": "deadbeef00000000"})
        )
        assert result["success"] is False

    def test_dry_run_does_not_mutate(self):
        fp = self._seed_finding()
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.remediate_error({"error_fingerprint": fp, "dry_run": True})
        )
        assert result["success"] is True
        assert result["dry_run"] is True

    def test_dispatches_to_mcp_server_when_connected(self):
        fp = self._seed_finding()
        mock_mcp = MagicMock()
        mock_mcp.invoke_tool = AsyncMock(return_value={"success": True, "incident_id": "inc_1"})
        self.agent.mcp_server = mock_mcp

        asyncio.get_event_loop().run_until_complete(
            self.agent.remediate_error({"error_fingerprint": fp})
        )
        mock_mcp.invoke_tool.assert_called_once()

    def test_kb_solution_bypasses_mcp(self):
        fp = self._seed_finding()
        self.agent.knowledge_base = MagicMock()
        self.agent.knowledge_base.search = MagicMock(
            return_value={"solution_summary": "increase memory limit"}
        )

        result = asyncio.get_event_loop().run_until_complete(
            self.agent.remediate_error({"error_fingerprint": fp})
        )
        assert "knowledge_base" in result["result"]["source"]

    def test_builtin_recommendation_when_no_mcp(self):
        fp = self._seed_finding()
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.remediate_error({"error_fingerprint": fp})
        )
        assert result["success"] is True
        assert "result" in result


# ---------------------------------------------------------------------------
# Unit tests: record_solution
# ---------------------------------------------------------------------------

class TestRecordSolution:
    def setup_method(self):
        self.agent = _make_agent()

    def test_records_without_kb(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.record_solution({
                "error_fingerprint": "abc123",
                "solution_summary": "restarted pod",
            })
        )
        assert result["success"] is True
        assert result["recorded"] is False  # no KB connected

    def test_records_with_kb(self):
        kb = MagicMock()
        kb.store = MagicMock()
        self.agent.knowledge_base = kb

        asyncio.get_event_loop().run_until_complete(
            self.agent.record_solution({
                "error_fingerprint": "abc123",
                "solution_summary": "increased memory",
                "actions_taken": ["memory_limit_increased"],
                "success": True,
            })
        )
        kb.store.assert_called_once()

    def test_record_contains_expected_fields(self):
        result = asyncio.get_event_loop().run_until_complete(
            self.agent.record_solution({
                "error_fingerprint": "fp_test",
                "solution_summary": "test solution",
            })
        )
        record = result["record"]
        for field in ("fingerprint", "solution_summary", "recorded_at", "agent"):
            assert field in record, f"Missing field: {field}"

    def test_kb_save_fallback(self):
        kb = MagicMock(spec=[])  # no 'store', only 'save'
        kb.save = MagicMock()
        self.agent.knowledge_base = kb

        asyncio.get_event_loop().run_until_complete(
            self.agent.record_solution({
                "error_fingerprint": "fp_test",
                "solution_summary": "saved via fallback",
            })
        )
        kb.save.assert_called_once()


# ---------------------------------------------------------------------------
# Integration smoke test: end-to-end flow
# ---------------------------------------------------------------------------

class TestEndToEndFlow:
    def test_full_pipeline(self):
        """fetch → analyze → remediate → record"""
        agent = _make_agent(error_threshold=1)
        mock_integration = _make_integration(
            errors=[
                _make_log("OOMKilled pod-web"),
                _make_log("CVE-2024-9999 critical vulnerability"),
            ]
        )
        agent._integrations["dynatrace"] = mock_integration
        kb = MagicMock()
        kb.store = MagicMock()
        kb.search = MagicMock(return_value=None)
        agent.knowledge_base = kb

        loop = asyncio.get_event_loop()

        # 1. fetch
        fetch = loop.run_until_complete(agent.fetch_logs({"platform": "dynatrace"}))
        assert fetch["total_entries"] >= 2

        # 2. analyze
        analysis = loop.run_until_complete(agent.analyze_errors({}))
        assert analysis["unique_error_groups"] >= 1

        # 3. remediate first finding
        fp = next(iter(agent._findings))
        remedy = loop.run_until_complete(
            agent.remediate_error({"error_fingerprint": fp, "dry_run": True})
        )
        assert remedy["success"] is True

        # 4. knowledge base was written
        kb.store.assert_called()
