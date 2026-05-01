"""Agent Registry for dynamic agent selection and instantiation."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from lios.logging_setup import get_logger

if TYPE_CHECKING:
    from lios.agents.base_agent import BaseAgent

logger = get_logger(__name__)


@dataclass
class AgentRegistration:
    """Registration information for an agent."""

    name: str
    """Unique identifier for the agent (e.g., 'sustainability')"""

    class_name: str
    """Full class name including module (e.g., 'SustainabilityAgent')"""

    module_path: str
    """Module path where agent is defined (e.g., 'lios.agents.sustainability_agent')"""

    covers_regulations: list[str]
    """List of regulations this agent handles (e.g., ['CSRD', 'ESRS'])"""

    description: str = ""
    """Optional description of the agent's domain"""

    enabled: bool = True
    """Whether this agent is enabled"""

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, AgentRegistration):
            return self.name == other.name
        return False


class AgentRegistry:
    """Central registry for all available agents.

    This registry allows dynamic agent selection based on regulations
    and enables easy addition of new agents without modifying core code.
    """

    def __init__(self):
        """Initialize the agent registry with default agents."""
        self._registry: dict[str, AgentRegistration] = {}
        self._instances: dict[str, BaseAgent] = {}
        self._load_default_agents()

    def _load_default_agents(self) -> None:
        """Load default agents into the registry."""
        default_agents = [
            AgentRegistration(
                name="unified_compliance",
                class_name="UnifiedComplianceAgent",
                module_path="lios.agents.unified_agent",
                covers_regulations=["CSRD", "ESRS", "EU_TAXONOMY", "SFDR", "CS3D"],
                description="Full EU sustainability compliance: CSRD, ESRS, EU Taxonomy, SFDR, CS3D",
            ),
        ]

        for agent_reg in default_agents:
            self.register(agent_reg)
            logger.debug(f"Registered agent: {agent_reg.name}")

    def register(self, registration: AgentRegistration) -> None:
        """Register an agent.

        Args:
            registration: AgentRegistration instance

        Raises:
            ValueError: If agent name already registered
        """
        if registration.name in self._registry:
            logger.warning(
                f"Agent '{registration.name}' already registered, overwriting"
            )

        self._registry[registration.name] = registration
        logger.debug(f"Registered agent: {registration.name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an instantiated agent by name.

        Uses caching to avoid repeated instantiation.

        Args:
            name: Agent name

        Returns:
            BaseAgent instance or None if not found

        Raises:
            ImportError: If agent module cannot be imported
            AttributeError: If agent class cannot be found
        """
        if name not in self._registry:
            logger.warning(f"Agent '{name}' not found in registry")
            return None

        # Return cached instance if available
        if name in self._instances:
            return self._instances[name]

        registration = self._registry[name]

        if not registration.enabled:
            logger.warning(f"Agent '{name}' is disabled")
            return None

        # Dynamically import and instantiate
        try:
            module = importlib.import_module(registration.module_path)
            agent_class = getattr(module, registration.class_name)
            instance = agent_class()
            self._instances[name] = instance
            logger.debug(f"Instantiated agent: {name}")
            return instance
        except ImportError as e:
            logger.error(f"Failed to import agent module {registration.module_path}: {e}")
            raise
        except AttributeError as e:
            logger.error(
                f"Agent class {registration.class_name} not found in {registration.module_path}: {e}"
            )
            raise

    def get_agents_for_regulations(self, regulations: list[str]) -> list[BaseAgent]:
        """Get agents that handle specific regulations.

        Selects agents based on regulation coverage, respecting agent enablement.

        Args:
            regulations: List of regulation names (e.g., ['CSRD', 'ESRS'])

        Returns:
            List of instantiated agents covering the given regulations
        """
        if not regulations:
            logger.warning("No regulations specified, returning all agents")
            return [
                self.get_agent(name)
                for name in self._registry
                if self._registry[name].enabled
            ]

        selected_agents: dict[str, BaseAgent] = {}

        for regulation in regulations:
            # Find all agents that cover this regulation
            for agent_name, registration in self._registry.items():
                if (
                    regulation in registration.covers_regulations
                    and registration.enabled
                ):
                    if agent_name not in selected_agents:
                        agent = self.get_agent(agent_name)
                        if agent:
                            selected_agents[agent_name] = agent

        if not selected_agents:
            logger.warning(f"No agents found for regulations: {regulations}")

        return list(selected_agents.values())

    def get_regulations_by_agent(self, agent_name: str) -> list[str]:
        """Get list of regulations handled by an agent.

        Args:
            agent_name: Agent name

        Returns:
            List of regulation names this agent handles
        """
        if agent_name not in self._registry:
            return []
        return self._registry[agent_name].covers_regulations

    def list_agents(self) -> list[AgentRegistration]:
        """List all registered agents.

        Returns:
            List of AgentRegistration instances
        """
        return list(self._registry.values())

    def list_enabled_agents(self) -> list[AgentRegistration]:
        """List only enabled agents.

        Returns:
            List of enabled AgentRegistration instances
        """
        return [reg for reg in self._registry.values() if reg.enabled]

    def list_regulations(self) -> set[str]:
        """Get all unique regulations covered by registered agents.

        Returns:
            Set of regulation names
        """
        all_regs = set()
        for registration in self._registry.values():
            if registration.enabled:
                all_regs.update(registration.covers_regulations)
        return all_regs

    def enable_agent(self, name: str) -> None:
        """Enable an agent.

        Args:
            name: Agent name

        Raises:
            KeyError: If agent not found
        """
        if name not in self._registry:
            raise KeyError(f"Agent '{name}' not found")
        self._registry[name].enabled = True
        # Clear cached instance
        if name in self._instances:
            del self._instances[name]
        logger.info(f"Enabled agent: {name}")

    def disable_agent(self, name: str) -> None:
        """Disable an agent.

        Args:
            name: Agent name

        Raises:
            KeyError: If agent not found
        """
        if name not in self._registry:
            raise KeyError(f"Agent '{name}' not found")
        self._registry[name].enabled = False
        # Clear cached instance
        if name in self._instances:
            del self._instances[name]
        logger.info(f"Disabled agent: {name}")

    def clear_cache(self) -> None:
        """Clear all cached agent instances."""
        self._instances.clear()
        logger.debug("Cleared agent instance cache")


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_global_registry() -> AgentRegistry:
    """Get or create the global agent registry.

    Returns:
        Global AgentRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
        logger.info("Created global agent registry")
    return _global_registry
