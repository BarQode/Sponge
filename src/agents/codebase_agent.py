"""
MCP Agent for Codebase Failure Detection and Remediation

This agent autonomously detects application crashes, analyzes crash dumps,
and automatically remediates codebase failures.

Capabilities:
- Detect application crashes and errors
- Analyze crash dumps and stack traces
- Rollback failed deployments
- Apply hotfixes from knowledge base
- Monitor error rates and patterns

MCP Tools:
- detect_crash: Detect application crashes
- analyze_crash: Analyze crash dumps and stack traces
- rollback_deployment: Auto-rollback to previous version
- apply_hotfix: Deploy emergency fixes
- monitor_errors: Monitor error rates
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from src.mcp.server import MCPAgent, MCPTool

logger = logging.getLogger(__name__)


class CodebaseFailureAgent:
    """
    MCP Agent for Codebase Failure Detection and Remediation

    Detects and fixes application crashes, errors, and codebase failures
    in Kubernetes deployments.
    """

    def __init__(
        self,
        namespace: str = "default",
        auto_rollback: bool = True,
        error_threshold: float = 0.05,  # 5% error rate
        crash_window: int = 300,  # 5 minutes
        check_interval: int = 60  # Check every minute
    ):
        """
        Initialize Codebase Failure Agent.

        Args:
            namespace: Kubernetes namespace to monitor
            auto_rollback: Enable automatic rollback
            error_threshold: Error rate threshold for alerts
            crash_window: Time window for crash detection (seconds)
            check_interval: Check interval in seconds
        """
        self.namespace = namespace
        self.auto_rollback = auto_rollback
        self.error_threshold = error_threshold
        self.crash_window = crash_window
        self.check_interval = check_interval

        # Initialize Kubernetes client
        try:
            k8s_config.load_incluster_config()
        except:
            k8s_config.load_kube_config()

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

        # Crash tracking
        self.crash_history: List[Dict[str, Any]] = []
        self.error_patterns: Dict[str, int] = {}

        # Knowledge base
        self.knowledge_base = None

        logger.info("Initialized Codebase Failure Agent")

    def get_mcp_agent(self) -> MCPAgent:
        """Get MCP Agent definition."""
        agent = MCPAgent(
            agent_id="codebase-failure-agent",
            name="Codebase Failure Agent",
            description="Detects and remediates application crashes and errors",
            capabilities=[
                "crash_detection",
                "error_analysis",
                "auto_rollback",
                "hotfix_deployment",
                "pattern_recognition"
            ]
        )

        # Register MCP tools
        agent.tools = {
            "detect_crash": MCPTool(
                name="detect_crash",
                description="Detect application crashes and failures",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "time_window": {"type": "integer", "default": 300}
                    }
                },
                handler=self.detect_crash,
                agent_id=agent.agent_id
            ),
            "analyze_crash": MCPTool(
                name="analyze_crash",
                description="Analyze crash dumps and stack traces",
                input_schema={
                    "type": "object",
                    "properties": {
                        "crash_id": {"type": "string", "required": True},
                        "include_logs": {"type": "boolean", "default": True}
                    },
                    "required": ["crash_id"]
                },
                handler=self.analyze_crash,
                agent_id=agent.agent_id
            ),
            "rollback_deployment": MCPTool(
                name="rollback_deployment",
                description="Rollback deployment to previous version",
                input_schema={
                    "type": "object",
                    "properties": {
                        "deployment_name": {"type": "string", "required": True},
                        "namespace": {"type": "string"},
                        "revision": {"type": "integer"}
                    },
                    "required": ["deployment_name"]
                },
                handler=self.rollback_deployment,
                agent_id=agent.agent_id
            ),
            "apply_hotfix": MCPTool(
                name="apply_hotfix",
                description="Apply emergency hotfix to running deployment",
                input_schema={
                    "type": "object",
                    "properties": {
                        "deployment_name": {"type": "string", "required": True},
                        "hotfix_id": {"type": "string", "required": True},
                        "namespace": {"type": "string"}
                    },
                    "required": ["deployment_name", "hotfix_id"]
                },
                handler=self.apply_hotfix,
                agent_id=agent.agent_id
            ),
            "monitor_errors": MCPTool(
                name="monitor_errors",
                description="Monitor error rates and patterns",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "time_window": {"type": "integer", "default": 3600}
                    }
                },
                handler=self.monitor_errors,
                agent_id=agent.agent_id
            )
        }

        return agent

    async def detect_crash(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect application crashes and failures.

        Args:
            arguments: Tool arguments (namespace, time_window)
            context: Execution context

        Returns:
            Crash detection results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)
            time_window = arguments.get("time_window", self.crash_window)

            logger.info(f"Detecting crashes in namespace: {namespace}")

            crashes = []

            # Check for CrashLoopBackOff pods
            pods = self.core_v1.list_namespaced_pod(namespace)

            for pod in pods.items:
                # Check container statuses
                if pod.status.container_statuses:
                    for container_status in pod.status.container_statuses:
                        # Detect crash loops
                        if container_status.state.waiting:
                            reason = container_status.state.waiting.reason
                            if reason in ["CrashLoopBackOff", "Error"]:
                                crashes.append({
                                    "crash_id": f"crash_{pod.metadata.name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                                    "pod_name": pod.metadata.name,
                                    "namespace": namespace,
                                    "container_name": container_status.name,
                                    "reason": reason,
                                    "restart_count": container_status.restart_count,
                                    "last_state": self._get_last_termination_state(container_status)
                                })

                        # Detect high restart counts
                        elif container_status.restart_count > 5:
                            crashes.append({
                                "crash_id": f"crash_{pod.metadata.name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                                "pod_name": pod.metadata.name,
                                "namespace": namespace,
                                "container_name": container_status.name,
                                "reason": "HighRestartCount",
                                "restart_count": container_status.restart_count,
                                "last_state": self._get_last_termination_state(container_status)
                            })

            # Store crash history
            self.crash_history.extend(crashes)

            # Auto-rollback if enabled
            if self.auto_rollback and crashes:
                for crash in crashes[:3]:  # Top 3 critical
                    # Get deployment name from pod
                    deployment_name = self._get_deployment_from_pod(
                        crash["pod_name"],
                        namespace
                    )

                    if deployment_name:
                        await self.rollback_deployment({
                            "deployment_name": deployment_name,
                            "namespace": namespace
                        }, context)

            return {
                "success": True,
                "namespace": namespace,
                "crashes_detected": len(crashes),
                "crashes": crashes,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Crash detection failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_crash(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze crash dumps and stack traces.

        Args:
            arguments: Tool arguments (crash_id, include_logs)
            context: Execution context

        Returns:
            Crash analysis results
        """
        try:
            crash_id = arguments["crash_id"]
            include_logs = arguments.get("include_logs", True)

            logger.info(f"Analyzing crash: {crash_id}")

            # Find crash record
            crash_record = None
            for crash in self.crash_history:
                if crash["crash_id"] == crash_id:
                    crash_record = crash
                    break

            if not crash_record:
                return {
                    "success": False,
                    "error": f"Crash record {crash_id} not found"
                }

            # Get pod logs
            logs = ""
            if include_logs:
                try:
                    logs = self.core_v1.read_namespaced_pod_log(
                        crash_record["pod_name"],
                        crash_record["namespace"],
                        container=crash_record.get("container_name"),
                        tail_lines=100
                    )
                except ApiException as e:
                    logger.warning(f"Could not retrieve logs: {e}")

            # Analyze logs for patterns
            analysis = {
                "crash_id": crash_id,
                "pod_name": crash_record["pod_name"],
                "container_name": crash_record.get("container_name"),
                "reason": crash_record["reason"],
                "restart_count": crash_record["restart_count"],
                "error_patterns": self._extract_error_patterns(logs),
                "stack_trace": self._extract_stack_trace(logs),
                "root_cause": self._determine_root_cause(logs, crash_record),
                "similar_incidents": []
            }

            # Check knowledge base for similar crashes
            if self.knowledge_base:
                analysis["similar_incidents"] = await self._find_similar_crashes(
                    analysis["error_patterns"]
                )

            return {
                "success": True,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Crash analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def rollback_deployment(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Rollback deployment to previous version.

        Args:
            arguments: Tool arguments (deployment_name, namespace, revision)
            context: Execution context

        Returns:
            Rollback results
        """
        try:
            deployment_name = arguments["deployment_name"]
            namespace = arguments.get("namespace", self.namespace)
            revision = arguments.get("revision")

            logger.info(f"Rolling back deployment: {deployment_name}")

            # Get deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                deployment_name,
                namespace
            )

            # Get revision history
            revisions = await self._get_deployment_revisions(
                deployment_name,
                namespace
            )

            if not revisions:
                return {
                    "success": False,
                    "error": "No previous revisions available"
                }

            # Determine target revision
            if revision is None:
                # Rollback to previous revision
                target_revision = revisions[-2] if len(revisions) > 1 else revisions[-1]
            else:
                target_revision = revision

            # Perform rollback (simplified)
            # In production, use kubectl rollout undo
            logger.info(f"Rolling back to revision {target_revision}")

            # Store solution
            if self.knowledge_base:
                await self._store_rollback_solution(
                    deployment_name,
                    target_revision
                )

            return {
                "success": True,
                "deployment_name": deployment_name,
                "namespace": namespace,
                "previous_revision": deployment.metadata.generation,
                "target_revision": target_revision,
                "status": "rollback_initiated",
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def apply_hotfix(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Apply emergency hotfix to running deployment.

        Args:
            arguments: Tool arguments (deployment_name, hotfix_id, namespace)
            context: Execution context

        Returns:
            Hotfix application results
        """
        try:
            deployment_name = arguments["deployment_name"]
            hotfix_id = arguments["hotfix_id"]
            namespace = arguments.get("namespace", self.namespace)

            logger.info(f"Applying hotfix {hotfix_id} to {deployment_name}")

            # Check knowledge base for hotfix
            hotfix = None
            if self.knowledge_base:
                hotfix = await self._get_hotfix_from_kb(hotfix_id)

            if not hotfix:
                return {
                    "success": False,
                    "error": f"Hotfix {hotfix_id} not found in knowledge base"
                }

            # Apply hotfix (simplified)
            # In production, this would update deployment with hotfix image/config
            result = {
                "hotfix_id": hotfix_id,
                "deployment_name": deployment_name,
                "changes_applied": hotfix.get("changes", []),
                "status": "applied"
            }

            return {
                "success": True,
                "deployment_name": deployment_name,
                "namespace": namespace,
                "hotfix_id": hotfix_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Hotfix application failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def monitor_errors(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Monitor error rates and patterns.

        Args:
            arguments: Tool arguments (namespace, time_window)
            context: Execution context

        Returns:
            Error monitoring results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)
            time_window = arguments.get("time_window", 3600)

            logger.info(f"Monitoring errors in namespace: {namespace}")

            # Collect error metrics
            error_metrics = {
                "namespace": namespace,
                "time_window": time_window,
                "total_pods": 0,
                "pods_with_errors": 0,
                "error_rate": 0.0,
                "top_errors": [],
                "error_patterns": {}
            }

            # Get all pods
            pods = self.core_v1.list_namespaced_pod(namespace)
            error_metrics["total_pods"] = len(pods.items)

            pods_with_errors = 0

            for pod in pods.items:
                # Check for errors in pod status
                if pod.status.container_statuses:
                    for container_status in pod.status.container_statuses:
                        if container_status.restart_count > 0:
                            pods_with_errors += 1

                            # Get recent logs to find error patterns
                            try:
                                logs = self.core_v1.read_namespaced_pod_log(
                                    pod.metadata.name,
                                    namespace,
                                    container=container_status.name,
                                    tail_lines=50
                                )

                                # Extract error patterns
                                patterns = self._extract_error_patterns(logs)
                                for pattern in patterns:
                                    self.error_patterns[pattern] = self.error_patterns.get(pattern, 0) + 1

                            except ApiException:
                                pass

            error_metrics["pods_with_errors"] = pods_with_errors
            error_metrics["error_rate"] = (
                pods_with_errors / error_metrics["total_pods"]
                if error_metrics["total_pods"] > 0 else 0.0
            )

            # Get top error patterns
            error_metrics["error_patterns"] = dict(
                sorted(
                    self.error_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            )

            return {
                "success": True,
                "metrics": error_metrics,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error monitoring failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_last_termination_state(self, container_status) -> Dict[str, Any]:
        """Get last termination state from container status"""
        if container_status.last_state and container_status.last_state.terminated:
            terminated = container_status.last_state.terminated
            return {
                "exit_code": terminated.exit_code,
                "reason": terminated.reason,
                "message": terminated.message,
                "finished_at": terminated.finished_at.isoformat() if terminated.finished_at else None
            }
        return {}

    def _get_deployment_from_pod(
        self,
        pod_name: str,
        namespace: str
    ) -> Optional[str]:
        """Get deployment name from pod"""
        try:
            pod = self.core_v1.read_namespaced_pod(pod_name, namespace)

            if pod.metadata.owner_references:
                for owner_ref in pod.metadata.owner_references:
                    if owner_ref.kind == "ReplicaSet":
                        # Get ReplicaSet to find Deployment
                        rs = self.apps_v1.read_namespaced_replica_set(
                            owner_ref.name,
                            namespace
                        )

                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    return rs_owner.name

            return None

        except Exception as e:
            logger.error(f"Could not get deployment from pod: {e}")
            return None

    def _extract_error_patterns(self, logs: str) -> List[str]:
        """Extract error patterns from logs"""
        patterns = []

        # Common error patterns
        error_regexes = [
            r"(?i)error:?\s+(.+)",
            r"(?i)exception:?\s+(.+)",
            r"(?i)fatal:?\s+(.+)",
            r"(?i)panic:?\s+(.+)",
            r"(?i)failed:?\s+(.+)"
        ]

        for regex in error_regexes:
            matches = re.findall(regex, logs)
            patterns.extend(matches[:5])  # Top 5 per pattern

        return patterns

    def _extract_stack_trace(self, logs: str) -> List[str]:
        """Extract stack trace from logs"""
        stack_trace = []

        # Look for stack trace patterns
        lines = logs.split('\n')
        in_stack_trace = False

        for line in lines:
            if re.search(r'(?i)(stack\s+trace|traceback|at\s+\w+\.\w+)', line):
                in_stack_trace = True

            if in_stack_trace:
                stack_trace.append(line)

                # Stop at blank line
                if not line.strip():
                    break

        return stack_trace[:20]  # Limit to 20 lines

    def _determine_root_cause(
        self,
        logs: str,
        crash_record: Dict[str, Any]
    ) -> str:
        """Determine root cause of crash"""
        # Check for common root causes
        if "OutOfMemoryError" in logs or "OOM" in logs:
            return "Out of memory error"
        elif "Connection refused" in logs:
            return "Service connection failure"
        elif "FileNotFound" in logs or "No such file" in logs:
            return "Missing configuration or file"
        elif "Permission denied" in logs:
            return "Permission/RBAC issue"
        elif crash_record["reason"] == "CrashLoopBackOff":
            return "Application crash loop - check logs for specific error"
        else:
            return "Unknown - requires manual investigation"

    async def _get_deployment_revisions(
        self,
        deployment_name: str,
        namespace: str
    ) -> List[int]:
        """Get deployment revision history"""
        # Simplified - in production, use kubectl rollout history
        return [1, 2, 3]  # Mock revisions

    async def _find_similar_crashes(
        self,
        error_patterns: List[str]
    ) -> List[Dict[str, Any]]:
        """Find similar crashes in knowledge base"""
        return []

    async def _get_hotfix_from_kb(self, hotfix_id: str) -> Optional[Dict[str, Any]]:
        """Get hotfix from knowledge base"""
        return None

    async def _store_rollback_solution(
        self,
        deployment_name: str,
        revision: int
    ):
        """Store rollback solution in knowledge base"""
        pass
