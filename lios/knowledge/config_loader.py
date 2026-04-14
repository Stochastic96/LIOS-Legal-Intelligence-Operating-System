"""Configuration loader for regulations and compliance thresholds."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from lios.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class RegulationThresholds:
    """Compliance thresholds for a regulation."""

    large_enterprise: dict[str, int | float] = field(default_factory=dict)
    """Thresholds for large enterprises"""

    medium_enterprise: dict[str, int | float] = field(default_factory=dict)
    """Thresholds for medium enterprises"""

    small_enterprise: dict[str, int | float] = field(default_factory=dict)
    """Thresholds for small enterprises"""

    def get_threshold(self, enterprise_size: str, key: str) -> Optional[int | float]:
        """Get a specific threshold value.

        Args:
            enterprise_size: 'large', 'medium', or 'small'
            key: Threshold key (e.g., 'employees_min')

        Returns:
            Threshold value or None if not found
        """
        normalized = enterprise_size.lower().strip()
        if normalized.endswith("_enterprise"):
            attr_name = normalized
        else:
            attr_name = f"{normalized}_enterprise"
        thresholds = getattr(self, attr_name, {})
        return thresholds.get(key)


@dataclass
class RegulationConfig:
    """Configuration for a single regulation."""

    name: str
    """Regulation name/code (e.g., 'CSRD')"""

    full_name: str
    """Full regulation name"""

    jurisdictions: list[str] = field(default_factory=list)
    """Jurisdictions where regulation applies"""

    effective_date: str = ""
    """Date when regulation became effective (YYYY-MM-DD)"""

    last_updated: str = ""
    """Last update date (YYYY-MM-DD)"""

    primary_agents: list[str] = field(default_factory=list)
    """Primary agents handling this regulation"""

    secondary_agents: list[str] = field(default_factory=list)
    """Secondary agents for supplementary analysis"""

    thresholds: RegulationThresholds = field(default_factory=RegulationThresholds)
    """Compliance thresholds"""

    description: str = ""
    """Regulation description"""

    enabled: bool = True
    """Whether regulation is enabled"""


class RegulationConfigLoader:
    """Load and manage regulation configurations from YAML files."""

    def __init__(self, config_dir: Path | str = "lios/config"):
        """Initialize the configuration loader.

        Args:
            config_dir: Directory containing YAML config files
        """
        self.config_dir = Path(config_dir)
        self.regulations: dict[str, RegulationConfig] = {}
        self._thresholds = self._load_default_thresholds()

    def _load_default_thresholds(self) -> dict[str, RegulationThresholds]:
        """Load default thresholds for all regulations.

        Returns:
            Dictionary of regulation name to thresholds
        """
        return {
            "CSRD": RegulationThresholds(
                large_enterprise={
                    "employees_min": 500,
                    "turnover_eur_min": 250_000_000,
                    "balance_sheet_eur_min": 125_000_000,
                },
                medium_enterprise={
                    "employees_min": 250,
                    "turnover_eur_min": 40_000_000,
                    "balance_sheet_eur_min": 20_000_000,
                },
            ),
            "ESRS": RegulationThresholds(
                large_enterprise={
                    "employees_min": 500,
                    "turnover_eur_min": 250_000_000,
                },
            ),
            "EU_TAXONOMY": RegulationThresholds(
                large_enterprise={
                    "employees_min": 500,
                    "turnover_eur_min": 250_000_000,
                },
            ),
            "SFDR": RegulationThresholds(
                large_enterprise={
                    "assets_under_management_min": 100_000_000,
                    "employees_min": 500,
                },
            ),
        }

    def register_regulation(self, config: RegulationConfig) -> None:
        """Register a regulation configuration.

        Args:
            config: RegulationConfig instance
        """
        self.regulations[config.name] = config
        # Merge thresholds if available
        if config.name in self._thresholds:
            config.thresholds = self._thresholds[config.name]
        logger.debug(f"Registered regulation config: {config.name}")

    def load_from_file(self, file_path: Path | str) -> None:
        """Load regulations from a YAML file.

        Args:
            file_path: Path to YAML configuration file

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"Config file not found: {file_path}")
            raise FileNotFoundError(f"Config file not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            if not data or "regulations" not in data:
                logger.warning(f"No regulations found in {file_path}")
                return

            for reg_name, reg_data in data["regulations"].items():
                config = RegulationConfig(
                    name=reg_data.get("name", reg_name),
                    full_name=reg_data.get("full_name", ""),
                    jurisdictions=reg_data.get("jurisdictions", []),
                    effective_date=reg_data.get("effective_date", ""),
                    last_updated=reg_data.get("last_updated", ""),
                    primary_agents=reg_data.get("primary_agents", []),
                    secondary_agents=reg_data.get("secondary_agents", []),
                    description=reg_data.get("description", ""),
                    enabled=reg_data.get("enabled", True),
                )
                self.register_regulation(config)
                logger.info(f"Loaded regulation from config: {reg_name}")

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {file_path}: {e}")
            raise

    def load_default_regulations(self) -> None:
        """Load default regulation configurations."""
        configs = [
            RegulationConfig(
                name="CSRD",
                full_name="Corporate Sustainability Reporting Directive",
                jurisdictions=["EU"],
                effective_date="2025-01-01",
                last_updated="2024-12-01",
                primary_agents=["sustainability", "supply_chain"],
                secondary_agents=["finance"],
                description="Requires large EU and non-EU companies to report sustainability",
            ),
            RegulationConfig(
                name="ESRS",
                full_name="European Sustainability Reporting Standards",
                jurisdictions=["EU"],
                effective_date="2024-01-01",
                last_updated="2024-12-01",
                primary_agents=["sustainability"],
                secondary_agents=[],
                description="Standards for sustainability disclosures under CSRD",
            ),
            RegulationConfig(
                name="EU_TAXONOMY",
                full_name="EU Taxonomy for Sustainable Activities",
                jurisdictions=["EU"],
                effective_date="2022-01-01",
                last_updated="2024-06-01",
                primary_agents=["finance"],
                secondary_agents=["sustainability"],
                description="Framework for classifying sustainable economy activities",
            ),
            RegulationConfig(
                name="SFDR",
                full_name="Sustainable Finance Disclosure Regulation",
                jurisdictions=["EU"],
                effective_date="2021-03-10",
                last_updated="2023-12-01",
                primary_agents=["finance"],
                secondary_agents=[],
                description="Requires financial market participants to disclose sustainability info",
            ),
        ]

        for config in configs:
            self.register_regulation(config)

    def get_regulation(self, name: str) -> Optional[RegulationConfig]:
        """Get regulation configuration by name.

        Args:
            name: Regulation name

        Returns:
            RegulationConfig or None
        """
        return self.regulations.get(name.upper())

    def get_all_regulations(self) -> list[RegulationConfig]:
        """Get all registered regulation configurations.

        Returns:
            List of RegulationConfig instances
        """
        return list(self.regulations.values())

    def get_enabled_regulations(self) -> list[RegulationConfig]:
        """Get all enabled regulation configurations.

        Returns:
            List of enabled RegulationConfig instances
        """
        return [reg for reg in self.regulations.values() if reg.enabled]

    def get_regulations_by_jurisdiction(self, jurisdiction: str) -> list[RegulationConfig]:
        """Get regulations applicable to a jurisdiction.

        Args:
            jurisdiction: Jurisdiction name (e.g., 'Germany', 'EU')

        Returns:
            List of applicable RegulationConfig instances
        """
        return [
            reg
            for reg in self.regulations.values()
            if jurisdiction.upper() in [j.upper() for j in reg.jurisdictions]
        ]

    def get_regulations_by_agent(self, agent_name: str) -> list[RegulationConfig]:
        """Get regulations covered by an agent.

        Args:
            agent_name: Agent name

        Returns:
            List of applicable RegulationConfig instances
        """
        return [
            reg
            for reg in self.regulations.values()
            if agent_name in reg.primary_agents + reg.secondary_agents
        ]

    def enable_regulation(self, name: str) -> None:
        """Enable a regulation.

        Args:
            name: Regulation name

        Raises:
            KeyError: If regulation not found
        """
        reg = self.get_regulation(name)
        if reg is None:
            raise KeyError(f"Regulation '{name}' not found")
        reg.enabled = True
        logger.info(f"Enabled regulation: {name}")

    def disable_regulation(self, name: str) -> None:
        """Disable a regulation.

        Args:
            name: Regulation name

        Raises:
            KeyError: If regulation not found
        """
        reg = self.get_regulation(name)
        if reg is None:
            raise KeyError(f"Regulation '{name}' not found")
        reg.enabled = False
        logger.info(f"Disabled regulation: {name}")

    def get_threshold(
        self, regulation: str, enterprise_size: str, key: str
    ) -> Optional[int | float]:
        """Get a specific threshold for a regulation.

        Args:
            regulation: Regulation name
            enterprise_size: 'large', 'medium', or 'small'
            key: Threshold key

        Returns:
            Threshold value or None
        """
        reg = self.get_regulation(regulation)
        if reg is None:
            return None
        return reg.thresholds.get_threshold(enterprise_size, key)


# Global configuration loader instance
_global_config_loader: Optional[RegulationConfigLoader] = None


def get_config_loader() -> RegulationConfigLoader:
    """Get or create the global configuration loader.

    Returns:
        Global RegulationConfigLoader instance
    """
    global _global_config_loader
    if _global_config_loader is None:
        _global_config_loader = RegulationConfigLoader()
        _global_config_loader.load_default_regulations()
        logger.info("Created global configuration loader with defaults")
    return _global_config_loader
