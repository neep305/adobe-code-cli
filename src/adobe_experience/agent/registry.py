"""Registry for supervisor-routed agent implementations."""

from typing import Dict, List, Optional

from adobe_experience.agent.contracts import AgentContract, Capability, ExecutionContext


class AgentRegistry:
    """In-memory registry for capability-based agent routing."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentContract] = {}

    def register(self, agent: AgentContract) -> None:
        """Register a new agent implementation.

        Raises:
            ValueError: if agent name already exists or has no capability.
        """
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' is already registered")
        if not agent.capabilities:
            raise ValueError(f"Agent '{agent.name}' must declare at least one capability")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[AgentContract]:
        """Get a registered agent by name."""
        return self._agents.get(name)

    def list_agents(self, capability: Optional[Capability] = None) -> List[AgentContract]:
        """List agents, optionally filtered by capability."""
        agents = list(self._agents.values())
        if capability is not None:
            agents = [agent for agent in agents if capability in agent.capabilities]
        return sorted(agents, key=lambda agent: agent.priority, reverse=True)

    def match(self, context: ExecutionContext, capability: Optional[Capability] = None) -> List[AgentContract]:
        """Find agents that can handle the given context.

        Matching order is deterministic: priority (desc), then name (asc).
        """
        candidates = self.list_agents(capability=capability)
        matched = [agent for agent in candidates if agent.can_handle(context)]
        return sorted(matched, key=lambda agent: (-agent.priority, agent.name))

    def names(self) -> List[str]:
        """Return agent names sorted for stable output."""
        return sorted(self._agents.keys())


def register_default_agents(registry: AgentRegistry) -> None:
    """Register built-in domain agents used by supervisor routing."""
    from adobe_experience.agent.agents import DataAnalysisAgent, SchemaMappingAgent

    if registry.get(DataAnalysisAgent.name) is None:
        registry.register(DataAnalysisAgent())
    if registry.get(SchemaMappingAgent.name) is None:
        registry.register(SchemaMappingAgent())
