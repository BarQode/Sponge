"""
MCP Agent for Observability Log Analysis and Remediation

Connects to Dynatrace, CloudWatch, Datadog, Splunk, Grafana, and other
monitoring platforms to fetch logs and metrics, runs ML-based error analysis,
and uses MCP to locate and deploy solutions — recording every resolved incident
in the knowledge base.

Capabilities:
- Multi-platform log ingestion (Dynatrace, CloudWatch, Datadog, Splunk, Grafana, etc.)
- Error pattern detection and anomaly classification
- Root-cause inference using correlated metrics + logs
- MCP-coordinated remediation dispatch to specialist agents
- Knowledge base recording of every solution

MCP Tools:
- fetch_logs        – Pull logs from one or all configured platforms
- analyze_errors    – Classify errors and infer root causes
- correlate_signals – Cross-correlate logs, metrics, and traces
- remediate_error   – Dispatch MCP remediation for a detected error
- record_solution   – Persist solution to knowledge base
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.integrations.base import LogEntry
from src.mcp.server import MCPAgent, MCPTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported platform keys and their import paths
# ---------------------------------------------------------------------------
PLATFORM_REGISTRY: Dict[str, str] = {
    "dynatrace":   "src.integrations.dynatrace.DynatraceIntegration",
    "cloudwatch":  "src.integrations.aws_cloudwatch.CloudWatchIntegration",
    "datadog":     "src.integrations.datadog.DatadogIntegration",
    "splunk":      "src.integrations.splunk.SplunkIntegration",
    "grafana":     "src.integrations.grafana.GrafanaIntegration",
    "elastic":     "src.integrations.elastic.ElasticIntegration",
    "sumologic":   "src.integrations.sumologic.SumoLogicIntegration",
    "sentry":      "src.integrations.sentry.SentryIntegration",
    "prometheus":  "src.integrations.prometheus.PrometheusIntegration",
    "logstash":    "src.integrations.logstash.LogstashIntegration",
    "papertrail":  "src.integrations.papertrail.PapertrailIntegration",
    "loggly":      "src.integrations.loggly.LogglyIntegration",
}

# Map error patterns to incident types understood by the remediation orchestrator
_INCIDENT_TYPE_MAP: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"OutOfMemory|OOMKilled|Cannot allocate memory", re.I), "oom"),
    (re.compile(r"CVE-\d{4}-\d+|vulnerable|critical\s+vuln", re.I),    "dependency"),
    (re.compile(r"RBAC|Forbidden|403|unauthorized|secret\s+exposed", re.I), "security"),
    (re.compile(r"terraform|drift|state\s+mismatch", re.I),             "terraform_drift"),
    (re.compile(r"CrashLoopBackOff|panic:|exception|segfault|core\s+dump", re.I), "codebase_failure"),
]


def _classify_incident(message: str) -> str:
    """Return MCP incident type for a log message, or 'generic_error'."""
    for pattern, incident_type in _INCIDENT_TYPE_MAP:
        if pattern.search(message):
            return incident_type
    return "generic_error"


def _severity_rank(level: str) -> int:
    return {"CRITICAL": 4, "ERROR": 3, "WARNING": 2, "INFO": 1}.get(level.upper(), 0)


class LogAnalysisAgent:
    """
    MCP Agent for multi-platform log analysis and automated remediation.

    Fetches logs from any configured observability platform, classifies errors,
    correlates signals across platforms, and dispatches MCP remediations —
    storing every solution in the project knowledge base.
    """

    def __init__(
        self,
        platform_configs: Dict[str, Dict[str, Any]],
        default_lookback_minutes: int = 60,
        error_threshold: int = 5,          # occurrences before auto-remediate
        auto_remediate: bool = True,
        knowledge_base=None,               # injected at runtime
        mcp_server=None,                   # injected at runtime
    ):
        """
        Args:
            platform_configs: ``{platform_key: {config_dict}}``
                e.g. ``{"dynatrace": {"api_token": "…", "environment_url": "…"}}``
            default_lookback_minutes: Default analysis window.
            error_threshold: Min occurrences to trigger auto-remediation.
            auto_remediate: Enable automatic remediation dispatch.
            knowledge_base: Knowledge base instance (optional at init time).
            mcp_server: MCPServer instance for dispatching to other agents.
        """
        self.platform_configs = platform_configs
        self.default_lookback_minutes = default_lookback_minutes
        self.error_threshold = error_threshold
        self.auto_remediate = auto_remediate
        self.knowledge_base = knowledge_base
        self.mcp_server = mcp_server

        # Lazily instantiated integration objects
        self._integrations: Dict[str, Any] = {}

        # In-memory findings cache (keyed by error fingerprint)
        self._findings: Dict[str, Dict[str, Any]] = {}

        logger.info(
            "Initialized LogAnalysisAgent with platforms: %s",
            list(platform_configs.keys()),
        )

    # ------------------------------------------------------------------
    # MCP agent descriptor
    # ------------------------------------------------------------------

    def get_mcp_agent(self) -> MCPAgent:
        """Return the MCPAgent descriptor for registration on the MCP server."""
        agent = MCPAgent(
            agent_id="log-analysis-agent",
            name="Log Analysis Agent",
            description=(
                "Fetches logs from Dynatrace, CloudWatch, Datadog, Splunk, and other "
                "observability platforms; classifies errors; and dispatches MCP "
                "remediations, recording every solution in the knowledge base."
            ),
            capabilities=[
                "multi_platform_log_ingestion",
                "error_classification",
                "signal_correlation",
                "mcp_remediation_dispatch",
                "knowledge_base_recording",
            ],
        )

        agent.tools = {
            "fetch_logs": MCPTool(
                name="fetch_logs",
                description="Fetch logs from one or all configured platforms",
                input_schema={
                    "type": "object",
                    "properties": {
                        "platform": {
                            "type": "string",
                            "description": (
                                "Platform key (dynatrace, cloudwatch, datadog, splunk, …). "
                                "Omit to query all configured platforms."
                            ),
                        },
                        "lookback_minutes": {
                            "type": "integer",
                            "default": 60,
                            "description": "How far back to fetch logs (minutes).",
                        },
                        "severity_filter": {
                            "type": "string",
                            "enum": ["ALL", "WARNING", "ERROR", "CRITICAL"],
                            "default": "ERROR",
                        },
                        "query": {
                            "type": "string",
                            "description": "Platform-native search query to narrow results.",
                        },
                    },
                },
                handler=self.fetch_logs,
                agent_id=agent.agent_id,
            ),
            "analyze_errors": MCPTool(
                name="analyze_errors",
                description="Classify errors and infer root causes from fetched logs",
                input_schema={
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string"},
                        "lookback_minutes": {"type": "integer", "default": 60},
                        "top_n": {
                            "type": "integer",
                            "default": 10,
                            "description": "Return the top N error groups by frequency.",
                        },
                    },
                },
                handler=self.analyze_errors,
                agent_id=agent.agent_id,
            ),
            "correlate_signals": MCPTool(
                name="correlate_signals",
                description=(
                    "Cross-correlate logs, metrics, and traces across platforms "
                    "to identify the highest-confidence root cause."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "lookback_minutes": {"type": "integer", "default": 60},
                        "service": {
                            "type": "string",
                            "description": "Filter to a specific service or deployment.",
                        },
                    },
                },
                handler=self.correlate_signals,
                agent_id=agent.agent_id,
            ),
            "remediate_error": MCPTool(
                name="remediate_error",
                description=(
                    "Dispatch an MCP remediation action for a detected error "
                    "and record the solution in the knowledge base."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "error_fingerprint": {
                            "type": "string",
                            "description": "Fingerprint returned by analyze_errors.",
                            "required": True,
                        },
                        "dry_run": {"type": "boolean", "default": False},
                    },
                    "required": ["error_fingerprint"],
                },
                handler=self.remediate_error,
                agent_id=agent.agent_id,
            ),
            "record_solution": MCPTool(
                name="record_solution",
                description="Persist a resolved incident and its solution to the knowledge base",
                input_schema={
                    "type": "object",
                    "properties": {
                        "error_fingerprint": {"type": "string", "required": True},
                        "solution_summary": {"type": "string", "required": True},
                        "actions_taken": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "success": {"type": "boolean", "default": True},
                    },
                    "required": ["error_fingerprint", "solution_summary"],
                },
                handler=self.record_solution,
                agent_id=agent.agent_id,
            ),
        }

        return agent

    # ------------------------------------------------------------------
    # MCP Tool Handlers
    # ------------------------------------------------------------------

    async def fetch_logs(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch logs from one or all configured platforms."""
        platform_key = arguments.get("platform")
        lookback = arguments.get("lookback_minutes", self.default_lookback_minutes)
        severity = arguments.get("severity_filter", "ERROR")
        query = arguments.get("query")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback)

        targets = (
            [platform_key]
            if platform_key
            else list(self.platform_configs.keys())
        )

        all_entries: List[Dict[str, Any]] = []
        errors: List[str] = []

        for key in targets:
            try:
                integration = self._get_integration(key)
                if integration is None:
                    errors.append(f"{key}: integration unavailable")
                    continue

                if severity in ("ERROR", "CRITICAL", "ALL"):
                    raw_logs = await asyncio.to_thread(
                        integration.fetch_errors, start_time, end_time,
                        {"query": query} if query else None,
                    )
                else:
                    raw_logs = await asyncio.to_thread(
                        integration.fetch_logs, start_time, end_time,
                        {"query": query} if query else None,
                    )

                # Apply severity filter
                min_rank = _severity_rank(severity) if severity != "ALL" else 0
                filtered = [
                    e for e in raw_logs
                    if _severity_rank(e.level) >= min_rank
                ]

                all_entries.extend([e.to_dict() for e in filtered])
                logger.info("Fetched %d entries from %s", len(filtered), key)

            except Exception as exc:
                logger.error("Error fetching from %s: %s", key, exc)
                errors.append(f"{key}: {exc}")

        return {
            "success": True,
            "platforms_queried": targets,
            "total_entries": len(all_entries),
            "entries": all_entries[:500],  # cap to avoid huge payloads
            "errors": errors,
            "window": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def analyze_errors(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Classify errors and infer root causes."""
        top_n = arguments.get("top_n", 10)

        # Fetch logs first
        fetch_result = await self.fetch_logs(
            {
                "platform": arguments.get("platform"),
                "lookback_minutes": arguments.get("lookback_minutes", self.default_lookback_minutes),
                "severity_filter": "ERROR",
            },
            context,
        )

        if not fetch_result["success"]:
            return fetch_result

        entries = fetch_result["entries"]

        # Group by fingerprint
        groups: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            msg = entry.get("message", "")
            fp = self._fingerprint(msg)
            if fp not in groups:
                groups[fp] = {
                    "fingerprint": fp,
                    "sample_message": msg[:300],
                    "incident_type": _classify_incident(msg),
                    "severity": entry.get("level", "ERROR"),
                    "sources": set(),
                    "count": 0,
                    "first_seen": entry.get("timestamp"),
                    "last_seen": entry.get("timestamp"),
                }
            g = groups[fp]
            g["count"] += 1
            g["sources"].add(entry.get("source", "unknown"))
            g["last_seen"] = entry.get("timestamp")

        # Sort by count
        ranked = sorted(groups.values(), key=lambda x: x["count"], reverse=True)[:top_n]

        # Serialise sets
        for g in ranked:
            g["sources"] = list(g["sources"])
            self._findings[g["fingerprint"]] = g

        # Auto-remediate high-frequency errors
        if self.auto_remediate:
            for g in ranked:
                if g["count"] >= self.error_threshold:
                    asyncio.create_task(
                        self.remediate_error(
                            {"error_fingerprint": g["fingerprint"]}, context
                        )
                    )

        return {
            "success": True,
            "total_entries_analysed": len(entries),
            "unique_error_groups": len(groups),
            "top_errors": ranked,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def correlate_signals(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Cross-correlate logs and metrics across all platforms."""
        lookback = arguments.get("lookback_minutes", self.default_lookback_minutes)
        service_filter = arguments.get("service")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback)

        correlations: List[Dict[str, Any]] = []

        for key, config in self.platform_configs.items():
            try:
                integration = self._get_integration(key)
                if integration is None:
                    continue

                # Fetch metrics alongside logs
                metrics = await asyncio.to_thread(
                    integration.fetch_performance_metrics,
                    start_time, end_time, None,
                )
                errors = await asyncio.to_thread(
                    integration.fetch_errors, start_time, end_time, None,
                )

                # Simple time-proximity correlation: errors within 60s of a metric spike
                for err in errors:
                    related_metrics = [
                        m for m in metrics
                        if abs((m.timestamp - err.timestamp).total_seconds()) < 60
                        and m.value > 0
                    ]
                    if related_metrics:
                        correlations.append({
                            "platform": key,
                            "error": err.message[:200],
                            "error_time": err.timestamp.isoformat(),
                            "incident_type": _classify_incident(err.message),
                            "correlated_metrics": [
                                {
                                    "name": m.metric_name,
                                    "value": m.value,
                                    "unit": m.unit,
                                }
                                for m in related_metrics[:5]
                            ],
                            "confidence": min(0.5 + 0.1 * len(related_metrics), 1.0),
                        })
            except Exception as exc:
                logger.warning("Correlation failed for %s: %s", key, exc)

        # Apply service filter
        if service_filter:
            correlations = [
                c for c in correlations
                if service_filter.lower() in c["error"].lower()
            ]

        correlations.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "success": True,
            "correlations_found": len(correlations),
            "correlations": correlations[:50],
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def remediate_error(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch MCP remediation for a detected error."""
        fingerprint = arguments["error_fingerprint"]
        dry_run = arguments.get("dry_run", False)

        finding = self._findings.get(fingerprint)
        if not finding:
            return {"success": False, "error": f"Unknown fingerprint: {fingerprint}"}

        incident_type = finding["incident_type"]
        severity = "critical" if finding["count"] >= self.error_threshold * 2 else "high"

        logger.info(
            "Dispatching remediation: type=%s severity=%s dry_run=%s",
            incident_type, severity, dry_run,
        )

        # Check knowledge base for a known solution first
        kb_solution = await self._query_knowledge_base(fingerprint, incident_type)

        if kb_solution:
            logger.info("Applying known KB solution for %s", fingerprint)
            result = {
                "source": "knowledge_base",
                "solution": kb_solution,
                "applied": not dry_run,
            }
        elif self.mcp_server:
            # Dispatch to the remediation orchestrator via MCP
            tool_name = "remediation-orchestrator.receive_incident"
            result = await self.mcp_server.invoke_tool(
                tool_name,
                {
                    "incident_type": incident_type,
                    "severity": severity,
                    "source_agent": "log-analysis-agent",
                    "incident_data": {
                        "fingerprint": fingerprint,
                        "sample_message": finding["sample_message"],
                        "count": finding["count"],
                        "sources": finding["sources"],
                        "dry_run": dry_run,
                    },
                },
                context,
            )
        else:
            result = {
                "source": "builtin",
                "recommendation": self._builtin_recommendation(incident_type),
                "applied": False,
                "note": "No MCP server connected — recommendation only",
            }

        # Record outcome regardless
        await self.record_solution(
            {
                "error_fingerprint": fingerprint,
                "solution_summary": str(result.get("solution") or result.get("recommendation", "dispatched")),
                "actions_taken": [f"incident_type={incident_type}", f"severity={severity}"],
                "success": result.get("success", True),
            },
            context,
        )

        return {
            "success": True,
            "fingerprint": fingerprint,
            "incident_type": incident_type,
            "severity": severity,
            "dry_run": dry_run,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def record_solution(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist a resolved incident and solution to the knowledge base."""
        fingerprint = arguments["error_fingerprint"]
        summary = arguments["solution_summary"]
        actions = arguments.get("actions_taken", [])
        success = arguments.get("success", True)

        record = {
            "fingerprint": fingerprint,
            "finding": self._findings.get(fingerprint, {}),
            "solution_summary": summary,
            "actions_taken": actions,
            "success": success,
            "recorded_at": datetime.utcnow().isoformat(),
            "agent": "log-analysis-agent",
        }

        if self.knowledge_base:
            try:
                await asyncio.to_thread(self._kb_store, record)
                logger.info("Stored solution for %s in knowledge base", fingerprint)
            except Exception as exc:
                logger.error("KB store failed: %s", exc)

        return {
            "success": True,
            "fingerprint": fingerprint,
            "recorded": self.knowledge_base is not None,
            "record": record,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_integration(self, platform_key: str) -> Optional[Any]:
        """Lazily instantiate and cache an integration object."""
        if platform_key in self._integrations:
            return self._integrations[platform_key]

        config = self.platform_configs.get(platform_key)
        if not config:
            logger.warning("No config for platform: %s", platform_key)
            return None

        import_path = PLATFORM_REGISTRY.get(platform_key)
        if not import_path:
            logger.warning("Unknown platform: %s", platform_key)
            return None

        try:
            module_path, class_name = import_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            instance = cls(config)
            self._integrations[platform_key] = instance
            logger.info("Loaded integration: %s", platform_key)
            return instance
        except Exception as exc:
            logger.error("Failed to load integration %s: %s", platform_key, exc)
            return None

    @staticmethod
    def _fingerprint(message: str) -> str:
        """Generate a stable fingerprint for grouping similar log messages.

        Strips variable parts (numbers, UUIDs, IPs) so that identical errors
        from different pods or time stamps cluster together.
        """
        normalized = re.sub(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<uuid>", message, flags=re.I)
        normalized = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<ip>", normalized)
        normalized = re.sub(r"\b\d+\b", "<n>", normalized)
        normalized = normalized.lower().strip()[:200]
        import hashlib
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def _query_knowledge_base(
        self, fingerprint: str, incident_type: str
    ) -> Optional[str]:
        """Return a cached solution from the knowledge base, if any."""
        if not self.knowledge_base:
            return None
        try:
            result = await asyncio.to_thread(
                self.knowledge_base.search, fingerprint, incident_type
            )
            if result:
                return result.get("solution_summary")
        except Exception:
            pass
        return None

    def _kb_store(self, record: Dict[str, Any]) -> None:
        """Synchronous KB write — called via asyncio.to_thread."""
        if hasattr(self.knowledge_base, "store"):
            self.knowledge_base.store(record)
        elif hasattr(self.knowledge_base, "save"):
            self.knowledge_base.save(record)

    @staticmethod
    def _builtin_recommendation(incident_type: str) -> str:
        recommendations = {
            "oom":              "Increase memory limits; consider HPA or VPA.",
            "dependency":       "Update vulnerable package; rebuild and push image.",
            "security":         "Review RBAC policies; rotate any exposed secrets.",
            "terraform_drift":  "Run `terraform plan` to confirm drift; apply correction.",
            "codebase_failure": "Check recent deployments; rollback if error rate elevated.",
            "generic_error":    "Review logs, check resource limits, and inspect recent changes.",
        }
        return recommendations.get(incident_type, recommendations["generic_error"])
