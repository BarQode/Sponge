"""
MCP Agent for Out-of-Memory (OOM) Detection and Remediation

This agent autonomously detects, analyzes, and remediates OOM issues in
Kubernetes clusters.

Capabilities:
- Monitor pod memory usage via Prometheus
- Detect OOM kills from Kubernetes events
- Predict OOM before it happens
- Auto-remediate by adjusting resources or scaling

MCP Tools:
- detect_oom: Scan for OOM events
- analyze_memory: Analyze memory usage patterns
- remediate_oom: Automatically fix OOM issues
- predict_oom: Predict future OOM events
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from src.mcp.server import MCPAgent, MCPTool

logger = logging.getLogger(__name__)


class OOMDetectionAgent:
    """
    MCP Agent for OOM Detection and Remediation

    Monitors Kubernetes clusters for out-of-memory conditions and
    automatically remediates them.
    """

    def __init__(
        self,
        namespace: str = "default",
        auto_remediate: bool = True,
        memory_threshold: float = 0.9,  # 90% memory usage triggers alert
        check_interval: int = 30  # Check every 30 seconds
    ):
        """
        Initialize OOM Detection Agent.

        Args:
            namespace: Kubernetes namespace to monitor
            auto_remediate: Enable automatic remediation
            memory_threshold: Memory usage threshold for alerts (0.0-1.0)
            check_interval: Check interval in seconds
        """
        self.namespace = namespace
        self.auto_remediate = auto_remediate
        self.memory_threshold = memory_threshold
        self.check_interval = check_interval

        # Initialize Kubernetes client
        try:
            k8s_config.load_incluster_config()  # Running in cluster
        except:
            k8s_config.load_kube_config()  # Running locally

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

        # OOM detection state
        self.oom_events: List[Dict[str, Any]] = []
        self.memory_history: Dict[str, List[float]] = {}

        # Knowledge base integration (will be connected later)
        self.knowledge_base = None

        logger.info(f"Initialized OOM Detection Agent for namespace: {namespace}")

    def get_mcp_agent(self) -> MCPAgent:
        """
        Get MCP Agent definition.

        Returns:
            MCPAgent with registered tools
        """
        agent = MCPAgent(
            agent_id="oom-detection-agent",
            name="OOM Detection Agent",
            description="Detects and remediates out-of-memory issues in Kubernetes",
            capabilities=[
                "oom_detection",
                "memory_analysis",
                "resource_adjustment",
                "auto_remediation"
            ]
        )

        # Register tools
        agent.tools = {
            "detect_oom": MCPTool(
                name="detect_oom",
                description="Detect OOM events in Kubernetes pods",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string", "default": "default"},
                        "time_range": {"type": "string", "default": "1h"}
                    }
                },
                handler=self.detect_oom,
                agent_id=agent.agent_id
            ),
            "analyze_memory": MCPTool(
                name="analyze_memory",
                description="Analyze memory usage patterns for a pod",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pod_name": {"type": "string", "required": True},
                        "namespace": {"type": "string", "default": "default"}
                    },
                    "required": ["pod_name"]
                },
                handler=self.analyze_memory,
                agent_id=agent.agent_id
            ),
            "remediate_oom": MCPTool(
                name="remediate_oom",
                description="Automatically remediate OOM issue",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pod_name": {"type": "string", "required": True},
                        "namespace": {"type": "string", "default": "default"},
                        "action": {
                            "type": "string",
                            "enum": ["increase_memory", "restart", "scale"],
                            "default": "increase_memory"
                        }
                    },
                    "required": ["pod_name"]
                },
                handler=self.remediate_oom,
                agent_id=agent.agent_id
            ),
            "predict_oom": MCPTool(
                name="predict_oom",
                description="Predict future OOM events based on trends",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string", "default": "default"}
                    }
                },
                handler=self.predict_oom,
                agent_id=agent.agent_id
            )
        }

        return agent

    async def detect_oom(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect OOM events in Kubernetes.

        Args:
            arguments: Tool arguments (namespace, time_range)
            context: Execution context

        Returns:
            Detection results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)
            time_range = arguments.get("time_range", "1h")

            logger.info(f"Detecting OOM events in namespace: {namespace}")

            # Get OOM events from Kubernetes
            oom_events = []

            # Query Kubernetes events for OOM kills
            events = self.core_v1.list_namespaced_event(namespace)

            for event in events.items:
                if "OOMKilled" in event.reason or "OOM" in event.message:
                    oom_events.append({
                        "pod_name": event.involved_object.name,
                        "namespace": event.involved_object.namespace,
                        "reason": event.reason,
                        "message": event.message,
                        "timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None,
                        "count": event.count
                    })

            # Get pods with memory pressure
            pods_with_pressure = await self._get_memory_pressure_pods(namespace)

            result = {
                "success": True,
                "namespace": namespace,
                "oom_events_count": len(oom_events),
                "oom_events": oom_events,
                "memory_pressure_pods": pods_with_pressure,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Store events for analysis
            self.oom_events.extend(oom_events)

            # Auto-remediate if enabled
            if self.auto_remediate and oom_events:
                for event in oom_events:
                    await self.remediate_oom({
                        "pod_name": event["pod_name"],
                        "namespace": event["namespace"]
                    }, context)

            return result

        except Exception as e:
            logger.error(f"OOM detection failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_memory(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze memory usage for a pod.

        Args:
            arguments: Tool arguments (pod_name, namespace)
            context: Execution context

        Returns:
            Memory analysis results
        """
        try:
            pod_name = arguments["pod_name"]
            namespace = arguments.get("namespace", self.namespace)

            logger.info(f"Analyzing memory for pod: {pod_name}")

            # Get pod details
            pod = self.core_v1.read_namespaced_pod(pod_name, namespace)

            # Get memory limits and requests
            containers_info = []
            for container in pod.spec.containers:
                resources = container.resources

                memory_request = None
                memory_limit = None

                if resources.requests:
                    memory_request = resources.requests.get("memory")
                if resources.limits:
                    memory_limit = resources.limits.get("memory")

                containers_info.append({
                    "name": container.name,
                    "memory_request": memory_request,
                    "memory_limit": memory_limit
                })

            # Get current memory usage from metrics (if available)
            # In production, integrate with Prometheus
            memory_usage = await self._get_pod_memory_usage(pod_name, namespace)

            # Analyze memory trend
            trend_analysis = self._analyze_memory_trend(pod_name)

            return {
                "success": True,
                "pod_name": pod_name,
                "namespace": namespace,
                "containers": containers_info,
                "current_usage": memory_usage,
                "trend_analysis": trend_analysis,
                "recommendations": self._generate_recommendations(
                    containers_info, memory_usage, trend_analysis
                )
            }

        except Exception as e:
            logger.error(f"Memory analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def remediate_oom(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Automatically remediate OOM issue.

        Args:
            arguments: Tool arguments (pod_name, namespace, action)
            context: Execution context

        Returns:
            Remediation results
        """
        try:
            pod_name = arguments["pod_name"]
            namespace = arguments.get("namespace", self.namespace)
            action = arguments.get("action", "increase_memory")

            logger.info(f"Remediating OOM for pod: {pod_name}, action: {action}")

            # Get pod details to find the deployment/statefulset
            pod = self.core_v1.read_namespaced_pod(pod_name, namespace)

            # Find the controller (Deployment, StatefulSet, etc.)
            owner_ref = None
            if pod.metadata.owner_references:
                owner_ref = pod.metadata.owner_references[0]

            remediation_result = {}

            if action == "increase_memory":
                # Increase memory limits
                remediation_result = await self._increase_memory_limits(
                    owner_ref, namespace
                )
            elif action == "restart":
                # Delete pod to trigger restart
                self.core_v1.delete_namespaced_pod(pod_name, namespace)
                remediation_result = {
                    "action": "restart",
                    "status": "Pod deleted, will be recreated"
                }
            elif action == "scale":
                # Scale up replicas
                remediation_result = await self._scale_deployment(
                    owner_ref, namespace, scale_up=True
                )

            # Store solution in knowledge base
            if self.knowledge_base:
                await self._store_solution(
                    pod_name, namespace, action, remediation_result
                )

            return {
                "success": True,
                "pod_name": pod_name,
                "namespace": namespace,
                "action": action,
                "result": remediation_result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"OOM remediation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def predict_oom(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict future OOM events.

        Args:
            arguments: Tool arguments (namespace)
            context: Execution context

        Returns:
            Prediction results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)

            logger.info(f"Predicting OOM events in namespace: {namespace}")

            # Get all pods
            pods = self.core_v1.list_namespaced_pod(namespace)

            at_risk_pods = []

            for pod in pods.items:
                # Analyze memory trend
                trend = self._analyze_memory_trend(pod.metadata.name)

                if trend.get("prediction") == "oom_likely":
                    at_risk_pods.append({
                        "pod_name": pod.metadata.name,
                        "risk_score": trend.get("risk_score", 0),
                        "estimated_time_to_oom": trend.get("time_to_oom"),
                        "current_usage_percent": trend.get("current_usage_percent")
                    })

            return {
                "success": True,
                "namespace": namespace,
                "at_risk_pods_count": len(at_risk_pods),
                "at_risk_pods": sorted(
                    at_risk_pods,
                    key=lambda x: x["risk_score"],
                    reverse=True
                ),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"OOM prediction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_memory_pressure_pods(self, namespace: str) -> List[Dict[str, Any]]:
        """Get pods under memory pressure"""
        # Implementation would integrate with Prometheus
        # For now, return empty list
        return []

    async def _get_pod_memory_usage(self, pod_name: str, namespace: str) -> Dict[str, Any]:
        """Get current memory usage for a pod"""
        # Implementation would integrate with Prometheus
        return {
            "current_bytes": 0,
            "usage_percent": 0
        }

    def _analyze_memory_trend(self, pod_name: str) -> Dict[str, Any]:
        """Analyze memory usage trend for a pod"""
        if pod_name not in self.memory_history:
            return {
                "prediction": "insufficient_data",
                "risk_score": 0
            }

        history = self.memory_history[pod_name]

        if len(history) < 5:
            return {
                "prediction": "insufficient_data",
                "risk_score": 0
            }

        # Simple trend analysis
        recent_avg = sum(history[-5:]) / 5
        overall_avg = sum(history) / len(history)

        if recent_avg > self.memory_threshold:
            return {
                "prediction": "oom_likely",
                "risk_score": recent_avg,
                "current_usage_percent": recent_avg * 100
            }

        return {
            "prediction": "normal",
            "risk_score": recent_avg,
            "current_usage_percent": recent_avg * 100
        }

    def _generate_recommendations(
        self,
        containers: List[Dict],
        usage: Dict,
        trend: Dict
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        if trend.get("prediction") == "oom_likely":
            recommendations.append("Increase memory limits immediately")
            recommendations.append("Consider horizontal pod autoscaling")

        for container in containers:
            if not container.get("memory_limit"):
                recommendations.append(
                    f"Set memory limit for container {container['name']}"
                )

        return recommendations

    async def _increase_memory_limits(
        self,
        owner_ref: Any,
        namespace: str
    ) -> Dict[str, Any]:
        """Increase memory limits for a deployment"""
        if not owner_ref or owner_ref.kind != "Deployment":
            return {"status": "Cannot increase memory: not a Deployment"}

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                owner_ref.name, namespace
            )

            # Increase memory limits by 50%
            for container in deployment.spec.template.spec.containers:
                if container.resources and container.resources.limits:
                    if "memory" in container.resources.limits:
                        current = container.resources.limits["memory"]
                        # Parse and increase (simplified)
                        new_limit = self._calculate_new_memory(current, 1.5)
                        container.resources.limits["memory"] = new_limit

            # Update deployment
            self.apps_v1.patch_namespaced_deployment(
                owner_ref.name, namespace, deployment
            )

            return {
                "status": "Memory limits increased",
                "deployment": owner_ref.name
            }

        except Exception as e:
            return {"status": f"Failed: {e}"}

    async def _scale_deployment(
        self,
        owner_ref: Any,
        namespace: str,
        scale_up: bool = True
    ) -> Dict[str, Any]:
        """Scale deployment replicas"""
        if not owner_ref or owner_ref.kind != "Deployment":
            return {"status": "Cannot scale: not a Deployment"}

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                owner_ref.name, namespace
            )

            current_replicas = deployment.spec.replicas or 1
            new_replicas = current_replicas + 1 if scale_up else max(1, current_replicas - 1)

            deployment.spec.replicas = new_replicas

            self.apps_v1.patch_namespaced_deployment(
                owner_ref.name, namespace, deployment
            )

            return {
                "status": "Deployment scaled",
                "deployment": owner_ref.name,
                "replicas": f"{current_replicas} -> {new_replicas}"
            }

        except Exception as e:
            return {"status": f"Failed: {e}"}

    def _calculate_new_memory(self, current: str, multiplier: float) -> str:
        """Calculate new memory value"""
        # Simplified - in production, properly parse memory units
        if current.endswith("Mi"):
            value = int(current[:-2])
            return f"{int(value * multiplier)}Mi"
        elif current.endswith("Gi"):
            value = int(current[:-2])
            return f"{int(value * multiplier)}Gi"
        return current

    async def _store_solution(
        self,
        pod_name: str,
        namespace: str,
        action: str,
        result: Dict[str, Any]
    ):
        """Store remediation solution in knowledge base"""
        if not self.knowledge_base:
            return

        solution = {
            "incident_type": "oom",
            "pod_name": pod_name,
            "namespace": namespace,
            "action": action,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "success": result.get("status", "").startswith("Failed") == False
        }

        # Store in knowledge base (to be implemented)
        pass
