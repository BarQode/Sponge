"""
Model Context Protocol (MCP) Server for Sponge Agent Framework

This module implements the core MCP server that orchestrates autonomous agents
for Kubernetes incident detection and remediation.

MCP Protocol: https://spec.modelcontextprotocol.io/

Features:
- Agent registration and lifecycle management
- Tool discovery and invocation
- Resource management
- Inter-agent communication
- Knowledge base integration
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable
    agent_id: str


@dataclass
class MCPResource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mime_type: str
    handler: Callable


@dataclass
class MCPAgent:
    """MCP Agent definition"""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    tools: Dict[str, MCPTool] = field(default_factory=dict)
    resources: Dict[str, MCPResource] = field(default_factory=dict)
    status: str = "initialized"  # initialized, running, stopped, error
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)


class MCPServer:
    """
    Model Context Protocol Server

    Orchestrates autonomous agents for Kubernetes incident response.
    Implements MCP protocol for agent communication and tool invocation.
    """

    def __init__(
        self,
        server_id: str = "sponge-mcp-server",
        host: str = "0.0.0.0",
        port: int = 8765
    ):
        """
        Initialize MCP Server.

        Args:
            server_id: Unique server identifier
            host: Server bind address
            port: Server port
        """
        self.server_id = server_id
        self.host = host
        self.port = port

        # Agent registry
        self.agents: Dict[str, MCPAgent] = {}

        # Tool registry (aggregated from all agents)
        self.tools: Dict[str, MCPTool] = {}

        # Resource registry
        self.resources: Dict[str, MCPResource] = {}

        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}

        # Server state
        self.running = False

        logger.info(f"Initialized MCP Server: {server_id}")

    async def start(self):
        """Start the MCP server"""
        logger.info(f"Starting MCP Server on {self.host}:{self.port}")
        self.running = True

        # Start background tasks
        asyncio.create_task(self._heartbeat_monitor())
        asyncio.create_task(self._health_check())

        logger.info("MCP Server started successfully")

    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping MCP Server")
        self.running = False

        # Stop all agents
        for agent_id in list(self.agents.keys()):
            await self.unregister_agent(agent_id)

        logger.info("MCP Server stopped")

    def register_agent(self, agent: MCPAgent) -> bool:
        """
        Register an agent with the MCP server.

        Args:
            agent: MCPAgent to register

        Returns:
            True if successful
        """
        try:
            if agent.agent_id in self.agents:
                logger.warning(f"Agent {agent.agent_id} already registered")
                return False

            # Register agent
            self.agents[agent.agent_id] = agent

            # Register agent's tools
            for tool_name, tool in agent.tools.items():
                full_name = f"{agent.agent_id}.{tool_name}"
                self.tools[full_name] = tool

            # Register agent's resources
            for resource_uri, resource in agent.resources.items():
                self.resources[resource_uri] = resource

            agent.status = "running"
            agent.last_heartbeat = datetime.utcnow()

            logger.info(
                f"Registered agent {agent.agent_id} with "
                f"{len(agent.tools)} tools and {len(agent.resources)} resources"
            )

            # Emit agent registered event
            self._emit_event("agent_registered", {"agent_id": agent.agent_id})

            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent.agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the MCP server.

        Args:
            agent_id: Agent ID to unregister

        Returns:
            True if successful
        """
        try:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found")
                return False

            agent = self.agents[agent_id]

            # Remove agent's tools
            for tool_name in list(agent.tools.keys()):
                full_name = f"{agent_id}.{tool_name}"
                if full_name in self.tools:
                    del self.tools[full_name]

            # Remove agent's resources
            for resource_uri in list(agent.resources.keys()):
                if resource_uri in self.resources:
                    del self.resources[resource_uri]

            # Remove agent
            del self.agents[agent_id]

            logger.info(f"Unregistered agent {agent_id}")

            # Emit agent unregistered event
            self._emit_event("agent_unregistered", {"agent_id": agent_id})

            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool.

        Args:
            tool_name: Tool name (format: agent_id.tool_name)
            arguments: Tool arguments
            context: Optional execution context

        Returns:
            Tool execution result
        """
        try:
            if tool_name not in self.tools:
                return {
                    "success": False,
                    "error": f"Tool {tool_name} not found",
                    "available_tools": list(self.tools.keys())
                }

            tool = self.tools[tool_name]

            # Validate arguments against schema
            # (In production, use jsonschema for validation)

            logger.info(f"Invoking tool: {tool_name}")

            # Execute tool handler
            result = await tool.handler(arguments, context)

            # Emit tool invoked event
            self._emit_event("tool_invoked", {
                "tool_name": tool_name,
                "agent_id": tool.agent_id,
                "success": result.get("success", False)
            })

            return result

        except Exception as e:
            logger.error(f"Tool invocation failed for {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        Get an MCP resource.

        Args:
            uri: Resource URI

        Returns:
            Resource data
        """
        try:
            if uri not in self.resources:
                return {
                    "success": False,
                    "error": f"Resource {uri} not found"
                }

            resource = self.resources[uri]

            logger.info(f"Getting resource: {uri}")

            # Execute resource handler
            data = await resource.handler()

            return {
                "success": True,
                "uri": uri,
                "name": resource.name,
                "mime_type": resource.mime_type,
                "data": data
            }

        except Exception as e:
            logger.error(f"Resource retrieval failed for {uri}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools.

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "agent_id": tool.agent_id
            }
            for name, tool in self.tools.items()
        ]

    def list_resources(self) -> List[Dict[str, Any]]:
        """
        List all available resources.

        Returns:
            List of resource definitions
        """
        return [
            {
                "uri": uri,
                "name": resource.name,
                "description": resource.description,
                "mime_type": resource.mime_type
            }
            for uri, resource in self.resources.items()
        ]

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents.

        Returns:
            List of agent information
        """
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "status": agent.status,
                "tools_count": len(agent.tools),
                "resources_count": len(agent.resources),
                "last_heartbeat": agent.last_heartbeat.isoformat()
            }
            for agent in self.agents.values()
        ]

    def on_event(self, event_name: str, handler: Callable):
        """
        Register an event handler.

        Args:
            event_name: Event name
            handler: Handler function
        """
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []

        self.event_handlers[event_name].append(handler)

    def _emit_event(self, event_name: str, data: Dict[str, Any]):
        """
        Emit an event to all registered handlers.

        Args:
            event_name: Event name
            data: Event data
        """
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Event handler failed for {event_name}: {e}")

    async def _heartbeat_monitor(self):
        """Monitor agent heartbeats"""
        while self.running:
            try:
                current_time = datetime.utcnow()

                for agent_id, agent in self.agents.items():
                    # Check if agent heartbeat is stale (>60 seconds)
                    if (current_time - agent.last_heartbeat).total_seconds() > 60:
                        logger.warning(f"Agent {agent_id} heartbeat timeout")
                        agent.status = "error"

                        # Emit agent error event
                        self._emit_event("agent_error", {
                            "agent_id": agent_id,
                            "error": "Heartbeat timeout"
                        })

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(30)

    async def _health_check(self):
        """Periodic health check"""
        while self.running:
            try:
                total_agents = len(self.agents)
                running_agents = sum(
                    1 for agent in self.agents.values()
                    if agent.status == "running"
                )

                logger.debug(
                    f"Health check: {running_agents}/{total_agents} agents running"
                )

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information.

        Returns:
            Server info dictionary
        """
        return {
            "server_id": self.server_id,
            "host": self.host,
            "port": self.port,
            "running": self.running,
            "agents_count": len(self.agents),
            "tools_count": len(self.tools),
            "resources_count": len(self.resources),
            "agents": self.list_agents()
        }
