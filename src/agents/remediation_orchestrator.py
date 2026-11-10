"""
MCP Remediation Orchestrator Agent

This agent coordinates incident response across all specialized agents and
deploys solutions when issues are detected.

Capabilities:
- Receive incidents from all detection agents
- Query knowledge base for solutions
- Deploy remediation actions
- Monitor remediation results
- Update knowledge base with outcomes
- Coordinate multi-step remediations

MCP Tools:
- receive_incident: Receive incident from detection agent
- query_solutions: Search knowledge base for solutions
- deploy_solution: Deploy remediation to cluster
- monitor_remediation: Track remediation progress
- escalate_incident: Escalate to human operators
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from kubernetes import client, config as k8s_config

from src.mcp.server import MCPAgent, MCPTool

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RemediationStatus(Enum):
    """Remediation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class RemediationOrchestrator:
    """
    MCP Remediation Orchestrator Agent

    Coordinates incident response and deploys solutions across
    all specialized agents.
    """

    def __init__(
        self,
        auto_deploy: bool = True,
        require_approval: bool = False,  # For critical incidents
        max_concurrent_remediations: int = 5,
        escalation_threshold: int = 3  # Escalate after 3 failures
    ):
        """
        Initialize Remediation Orchestrator.

        Args:
            auto_deploy: Enable automatic solution deployment
            require_approval: Require human approval for critical incidents
            max_concurrent_remediations: Max parallel remediations
            escalation_threshold: Failures before human escalation
        """
        self.auto_deploy = auto_deploy
        self.require_approval = require_approval
        self.max_concurrent_remediations = max_concurrent_remediations
        self.escalation_threshold = escalation_threshold

        # Initialize Kubernetes client
        try:
            k8s_config.load_incluster_config()
        except:
            k8s_config.load_kube_config()

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

        # Incident queue
        self.incident_queue: List[Dict[str, Any]] = []
        self.active_remediations: Dict[str, Dict[str, Any]] = {}

        # Solution cache
        self.solution_cache: Dict[str, List[Dict[str, Any]]] = {}

        # Knowledge base integration
        self.knowledge_base = None

        # Agent registry (references to specialized agents)
        self.agents: Dict[str, Any] = {}

        logger.info("Initialized Remediation Orchestrator")

    def get_mcp_agent(self) -> MCPAgent:
        """Get MCP Agent definition."""
        agent = MCPAgent(
            agent_id="remediation-orchestrator",
            name="Remediation Orchestrator Agent",
            description="Coordinates incident response and deploys solutions",
            capabilities=[
                "incident_orchestration",
                "solution_deployment",
                "multi_agent_coordination",
                "knowledge_base_integration",
                "auto_remediation"
            ]
        )

        # Register MCP tools
        agent.tools = {
            "receive_incident": MCPTool(
                name="receive_incident",
                description="Receive incident from detection agent",
                input_schema={
                    "type": "object",
                    "properties": {
                        "incident_type": {
                            "type": "string",
                            "enum": ["oom", "dependency", "security", "terraform_drift", "codebase_failure"],
                            "required": True
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "required": True
                        },
                        "source_agent": {"type": "string", "required": True},
                        "incident_data": {"type": "object", "required": True}
                    },
                    "required": ["incident_type", "severity", "source_agent", "incident_data"]
                },
                handler=self.receive_incident,
                agent_id=agent.agent_id
            ),
            "query_solutions": MCPTool(
                name="query_solutions",
                description="Search knowledge base for solutions",
                input_schema={
                    "type": "object",
                    "properties": {
                        "incident_id": {"type": "string", "required": True},
                        "similarity_threshold": {"type": "number", "default": 0.8}
                    },
                    "required": ["incident_id"]
                },
                handler=self.query_solutions,
                agent_id=agent.agent_id
            ),
            "deploy_solution": MCPTool(
                name="deploy_solution",
                description="Deploy remediation solution to cluster",
                input_schema={
                    "type": "object",
                    "properties": {
                        "incident_id": {"type": "string", "required": True},
                        "solution_id": {"type": "string", "required": True},
                        "dry_run": {"type": "boolean", "default": False}
                    },
                    "required": ["incident_id", "solution_id"]
                },
                handler=self.deploy_solution,
                agent_id=agent.agent_id
            ),
            "monitor_remediation": MCPTool(
                name="monitor_remediation",
                description="Monitor remediation progress and results",
                input_schema={
                    "type": "object",
                    "properties": {
                        "remediation_id": {"type": "string", "required": True}
                    },
                    "required": ["remediation_id"]
                },
                handler=self.monitor_remediation,
                agent_id=agent.agent_id
            ),
            "escalate_incident": MCPTool(
                name="escalate_incident",
                description="Escalate incident to human operators",
                input_schema={
                    "type": "object",
                    "properties": {
                        "incident_id": {"type": "string", "required": True},
                        "reason": {"type": "string", "required": True}
                    },
                    "required": ["incident_id", "reason"]
                },
                handler=self.escalate_incident,
                agent_id=agent.agent_id
            )
        }

        return agent

    async def receive_incident(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Receive incident from detection agent.

        Args:
            arguments: Tool arguments (incident_type, severity, source_agent, incident_data)
            context: Execution context

        Returns:
            Incident receipt confirmation
        """
        try:
            incident_type = arguments["incident_type"]
            severity = arguments["severity"]
            source_agent = arguments["source_agent"]
            incident_data = arguments["incident_data"]

            logger.info(f"Received {severity} {incident_type} incident from {source_agent}")

            # Create incident record
            incident_id = f"inc_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{incident_type}"

            incident = {
                "incident_id": incident_id,
                "incident_type": incident_type,
                "severity": severity,
                "source_agent": source_agent,
                "incident_data": incident_data,
                "received_at": datetime.utcnow().isoformat(),
                "status": "pending",
                "attempts": 0
            }

            # Add to queue
            self.incident_queue.append(incident)

            # Check if we should auto-deploy
            should_auto_deploy = (
                self.auto_deploy and
                (severity != "critical" or not self.require_approval) and
                len(self.active_remediations) < self.max_concurrent_remediations
            )

            if should_auto_deploy:
                # Query for solutions
                solutions_result = await self.query_solutions({
                    "incident_id": incident_id
                }, context)

                # Deploy best solution if found
                if solutions_result.get("success") and solutions_result.get("solutions"):
                    best_solution = solutions_result["solutions"][0]

                    await self.deploy_solution({
                        "incident_id": incident_id,
                        "solution_id": best_solution["solution_id"]
                    }, context)

            return {
                "success": True,
                "incident_id": incident_id,
                "queued": True,
                "auto_deploy_initiated": should_auto_deploy,
                "queue_position": len(self.incident_queue),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to receive incident: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def query_solutions(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search knowledge base for solutions.

        Args:
            arguments: Tool arguments (incident_id, similarity_threshold)
            context: Execution context

        Returns:
            Matching solutions
        """
        try:
            incident_id = arguments["incident_id"]
            similarity_threshold = arguments.get("similarity_threshold", 0.8)

            logger.info(f"Querying solutions for incident: {incident_id}")

            # Find incident
            incident = None
            for inc in self.incident_queue:
                if inc["incident_id"] == incident_id:
                    incident = inc
                    break

            if not incident:
                return {
                    "success": False,
                    "error": f"Incident {incident_id} not found"
                }

            # Check cache first
            cache_key = f"{incident['incident_type']}_{incident['severity']}"
            if cache_key in self.solution_cache:
                logger.info("Using cached solutions")
                return {
                    "success": True,
                    "incident_id": incident_id,
                    "solutions": self.solution_cache[cache_key],
                    "from_cache": True
                }

            # Query knowledge base
            solutions = []

            if self.knowledge_base:
                solutions = await self._query_knowledge_base(
                    incident,
                    similarity_threshold
                )
            else:
                # Fallback to built-in solutions
                solutions = self._get_builtin_solutions(incident)

            # Cache solutions
            self.solution_cache[cache_key] = solutions

            return {
                "success": True,
                "incident_id": incident_id,
                "solutions_found": len(solutions),
                "solutions": solutions,
                "from_cache": False,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Solution query failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def deploy_solution(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deploy remediation solution to cluster.

        Args:
            arguments: Tool arguments (incident_id, solution_id, dry_run)
            context: Execution context

        Returns:
            Deployment results
        """
        try:
            incident_id = arguments["incident_id"]
            solution_id = arguments["solution_id"]
            dry_run = arguments.get("dry_run", False)

            logger.info(f"Deploying solution {solution_id} for incident {incident_id}")

            # Find incident
            incident = None
            for inc in self.incident_queue:
                if inc["incident_id"] == incident_id:
                    incident = inc
                    break

            if not incident:
                return {
                    "success": False,
                    "error": f"Incident {incident_id} not found"
                }

            # Create remediation record
            remediation_id = f"rem_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            remediation = {
                "remediation_id": remediation_id,
                "incident_id": incident_id,
                "solution_id": solution_id,
                "status": RemediationStatus.PENDING.value,
                "started_at": datetime.utcnow().isoformat(),
                "dry_run": dry_run,
                "steps_completed": [],
                "steps_failed": []
            }

            self.active_remediations[remediation_id] = remediation

            # Execute deployment based on incident type
            deployment_result = await self._execute_deployment(
                incident,
                solution_id,
                dry_run
            )

            # Update remediation status
            if deployment_result["success"]:
                remediation["status"] = RemediationStatus.IN_PROGRESS.value
                remediation["deployment_result"] = deployment_result

                # Start monitoring
                asyncio.create_task(
                    self._monitor_remediation_background(remediation_id)
                )
            else:
                remediation["status"] = RemediationStatus.FAILED.value
                remediation["error"] = deployment_result.get("error")

                # Check if we should escalate
                incident["attempts"] += 1
                if incident["attempts"] >= self.escalation_threshold:
                    await self.escalate_incident({
                        "incident_id": incident_id,
                        "reason": f"Remediation failed {incident['attempts']} times"
                    }, context)

            return {
                "success": True,
                "remediation_id": remediation_id,
                "incident_id": incident_id,
                "solution_id": solution_id,
                "deployment_result": deployment_result,
                "dry_run": dry_run,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Solution deployment failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def monitor_remediation(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Monitor remediation progress and results.

        Args:
            arguments: Tool arguments (remediation_id)
            context: Execution context

        Returns:
            Remediation status
        """
        try:
            remediation_id = arguments["remediation_id"]

            logger.info(f"Monitoring remediation: {remediation_id}")

            if remediation_id not in self.active_remediations:
                return {
                    "success": False,
                    "error": f"Remediation {remediation_id} not found"
                }

            remediation = self.active_remediations[remediation_id]

            # Check current status
            status_check = await self._check_remediation_status(remediation)

            return {
                "success": True,
                "remediation_id": remediation_id,
                "status": remediation["status"],
                "progress": status_check.get("progress", 0),
                "steps_completed": remediation["steps_completed"],
                "steps_failed": remediation["steps_failed"],
                "current_check": status_check,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Remediation monitoring failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def escalate_incident(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Escalate incident to human operators.

        Args:
            arguments: Tool arguments (incident_id, reason)
            context: Execution context

        Returns:
            Escalation confirmation
        """
        try:
            incident_id = arguments["incident_id"]
            reason = arguments["reason"]

            logger.warning(f"Escalating incident {incident_id}: {reason}")

            # Find incident
            incident = None
            for inc in self.incident_queue:
                if inc["incident_id"] == incident_id:
                    incident = inc
                    break

            if not incident:
                return {
                    "success": False,
                    "error": f"Incident {incident_id} not found"
                }

            # Update incident status
            incident["status"] = RemediationStatus.ESCALATED.value
            incident["escalated_at"] = datetime.utcnow().isoformat()
            incident["escalation_reason"] = reason

            # In production, this would:
            # 1. Create PagerDuty/OpsGenie alert
            # 2. Send Slack notification
            # 3. Create incident ticket
            # 4. Email on-call engineer

            return {
                "success": True,
                "incident_id": incident_id,
                "escalated": True,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Incident escalation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _query_knowledge_base(
        self,
        incident: Dict[str, Any],
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """Query knowledge base for similar incidents and solutions"""
        # In production, this would use vector similarity search
        return []

    def _get_builtin_solutions(
        self,
        incident: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get built-in solutions for incident type"""
        incident_type = incident["incident_type"]

        solutions_map = {
            "oom": [
                {
                    "solution_id": "oom_increase_memory",
                    "name": "Increase Memory Limits",
                    "description": "Increase pod memory limits by 50%",
                    "confidence": 0.9,
                    "actions": ["increase_memory_limit"]
                },
                {
                    "solution_id": "oom_scale_horizontal",
                    "name": "Scale Horizontally",
                    "description": "Increase replica count",
                    "confidence": 0.8,
                    "actions": ["scale_replicas"]
                }
            ],
            "dependency": [
                {
                    "solution_id": "dep_patch_vulnerability",
                    "name": "Patch Vulnerability",
                    "description": "Update vulnerable dependency",
                    "confidence": 0.85,
                    "actions": ["patch_dependency", "rebuild_image"]
                }
            ],
            "security": [
                {
                    "solution_id": "sec_fix_rbac",
                    "name": "Fix RBAC Issue",
                    "description": "Correct RBAC permissions",
                    "confidence": 0.9,
                    "actions": ["update_rbac_policy"]
                }
            ],
            "terraform_drift": [
                {
                    "solution_id": "tf_apply_correction",
                    "name": "Apply Terraform Correction",
                    "description": "Run terraform apply to fix drift",
                    "confidence": 0.95,
                    "actions": ["terraform_apply"]
                }
            ],
            "codebase_failure": [
                {
                    "solution_id": "code_rollback",
                    "name": "Rollback Deployment",
                    "description": "Rollback to previous version",
                    "confidence": 0.9,
                    "actions": ["rollback_deployment"]
                }
            ]
        }

        return solutions_map.get(incident_type, [])

    async def _execute_deployment(
        self,
        incident: Dict[str, Any],
        solution_id: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Execute solution deployment"""
        try:
            incident_type = incident["incident_type"]

            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "would_execute": f"Deploy solution {solution_id} for {incident_type}"
                }

            # Route to appropriate agent based on incident type
            if incident_type == "oom" and "oom-agent" in self.agents:
                return await self.agents["oom-agent"].remediate_oom(
                    incident["incident_data"],
                    {}
                )
            elif incident_type == "dependency" and "dependency-agent" in self.agents:
                return await self.agents["dependency-agent"].patch_vulnerability(
                    incident["incident_data"],
                    {}
                )
            elif incident_type == "security" and "security-agent" in self.agents:
                return await self.agents["security-agent"].remediate_security(
                    incident["incident_data"],
                    {}
                )
            elif incident_type == "terraform_drift" and "terraform-agent" in self.agents:
                return await self.agents["terraform-agent"].apply_correction(
                    incident["incident_data"],
                    {}
                )
            elif incident_type == "codebase_failure" and "codebase-agent" in self.agents:
                return await self.agents["codebase-agent"].rollback_deployment(
                    incident["incident_data"],
                    {}
                )
            else:
                return {
                    "success": False,
                    "error": f"No handler for incident type: {incident_type}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _check_remediation_status(
        self,
        remediation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check current status of remediation"""
        # In production, check actual cluster state
        return {
            "progress": 75,
            "healthy": True,
            "errors": []
        }

    async def _monitor_remediation_background(self, remediation_id: str):
        """Background task to monitor remediation"""
        try:
            remediation = self.active_remediations[remediation_id]

            # Monitor for up to 5 minutes
            max_checks = 30
            check_interval = 10  # seconds

            for i in range(max_checks):
                await asyncio.sleep(check_interval)

                status = await self._check_remediation_status(remediation)

                if status["progress"] >= 100:
                    remediation["status"] = RemediationStatus.COMPLETED.value
                    remediation["completed_at"] = datetime.utcnow().isoformat()

                    # Store solution in knowledge base
                    if self.knowledge_base:
                        await self._store_successful_remediation(remediation)

                    logger.info(f"Remediation {remediation_id} completed successfully")
                    break

                if not status["healthy"]:
                    remediation["status"] = RemediationStatus.FAILED.value
                    remediation["failed_at"] = datetime.utcnow().isoformat()
                    logger.error(f"Remediation {remediation_id} failed")
                    break

        except Exception as e:
            logger.error(f"Background monitoring failed: {e}")

    async def _store_successful_remediation(self, remediation: Dict[str, Any]):
        """Store successful remediation in knowledge base"""
        pass
