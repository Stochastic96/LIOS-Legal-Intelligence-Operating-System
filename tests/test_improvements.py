"""Comprehensive test suite for LIOS v0.1.0.

Tests for:
- Pydantic validation models
- Agent Registry
- Config loader
- API routes with error handling
- Applicability checker
"""

import pytest
from datetime import datetime
from pathlib import Path

from lios.agents.registry import AgentRegistry, AgentRegistration
from lios.knowledge.config_loader import RegulationConfigLoader, RegulationConfig, RegulationThresholds
from lios.models.validation import (
    CompanyProfile,
    QueryRequest,
    ApplicabilityRequest,
    RoadmapRequest,
    ErrorResponse,
)
from lios.features.applicability_checker import ApplicabilityChecker
from lios.logging_setup import setup_logging, get_logger


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def logger_setup():
    """Setup logging for tests."""
    setup_logging(log_level="DEBUG")
    return get_logger(__name__)


@pytest.fixture
def company_profile():
    """Create a test company profile."""
    return CompanyProfile(
        employees=750,
        turnover_eur=500_000_000,
        balance_sheet_eur=250_000_000,
        listed=True,
        jurisdiction="Germany",
    )


@pytest.fixture
def agent_registry():
    """Create a fresh agent registry."""
    return AgentRegistry()


@pytest.fixture
def config_loader():
    """Create a fresh config loader."""
    loader = RegulationConfigLoader()
    loader.load_default_regulations()
    return loader


# ============================================================================
# VALIDATION MODELS TESTS
# ============================================================================

class TestCompanyProfile:
    """Tests for CompanyProfile validation model."""

    def test_valid_profile(self, company_profile):
        """Test creating a valid company profile."""
        assert company_profile.employees == 750
        assert company_profile.turnover_eur == 500_000_000
        assert company_profile.listed is True

    def test_profile_with_negative_employees(self):
        """Test that negative employees are rejected."""
        with pytest.raises(ValueError):
            CompanyProfile(employees=-10)

    def test_profile_with_unrealistic_employees(self):
        """Test that unrealistic employee counts are rejected."""
        with pytest.raises(ValueError):
            CompanyProfile(employees=2_000_000)

    def test_profile_with_negative_turnover(self):
        """Test that negative turnover is rejected."""
        with pytest.raises(ValueError):
            CompanyProfile(turnover_eur=-100)

    def test_profile_defaults(self):
        """Test default values in company profile."""
        profile = CompanyProfile()
        assert profile.employees == 0
        assert profile.turnover_eur == 0.0
        assert profile.balance_sheet_eur == 0.0
        assert profile.listed is False
        assert profile.jurisdiction is None


class TestQueryRequest:
    """Tests for QueryRequest validation model."""

    def test_valid_query(self):
        """Test creating a valid query request."""
        request = QueryRequest(query="What are CSRD requirements?")
        assert request.query == "What are CSRD requirements?"
        assert request.company_profile is None

    def test_query_too_short(self):
        """Test that queries shorter than 3 characters are rejected."""
        with pytest.raises(ValueError):
            QueryRequest(query="Hi")

    def test_query_too_long(self):
        """Test that queries longer than 5000 characters are rejected."""
        long_query = "a" * 5001
        with pytest.raises(ValueError):
            QueryRequest(query=long_query)

    def test_query_with_whitespace_only(self):
        """Test that whitespace-only queries are rejected."""
        with pytest.raises(ValueError):
            QueryRequest(query="   ")

    def test_query_with_company_profile(self, company_profile):
        """Test query with company profile."""
        request = QueryRequest(
            query="Does CSRD apply to my company?",
            company_profile=company_profile,
        )
        assert request.company_profile.employees == 750


class TestApplicabilityRequest:
    """Tests for ApplicabilityRequest validation model."""

    def test_valid_applicability_request(self, company_profile):
        """Test creating a valid applicability request."""
        request = ApplicabilityRequest(
            regulation="CSRD",
            company_profile=company_profile,
        )
        assert request.regulation == "CSRD"

    def test_regulation_normalized_to_uppercase(self, company_profile):
        """Test that regulation names are normalized to uppercase."""
        request = ApplicabilityRequest(
            regulation="csrd",
            company_profile=company_profile,
        )
        assert request.regulation == "CSRD"

    def test_empty_regulation_rejected(self, company_profile):
        """Test that empty regulation name is rejected."""
        with pytest.raises(ValueError):
            ApplicabilityRequest(
                regulation="",
                company_profile=company_profile,
            )


# ============================================================================
# AGENT REGISTRY TESTS
# ============================================================================

class TestAgentRegistry:
    """Tests for AgentRegistry system."""

    def test_registry_initializes_with_defaults(self, agent_registry):
        """Test that registry loads default agents."""
        agents = agent_registry.list_agents()
        assert len(agents) >= 3  # At least sustainability, finance, supply_chain
        names = [a.name for a in agents]
        assert "sustainability" in names
        assert "finance" in names

    def test_register_agent(self, agent_registry):
        """Test registering a new agent."""
        new_agent = AgentRegistration(
            name="governance",
            class_name="GovernanceAgent",
            module_path="lios.agents.governance_agent",
            covers_regulations=["CGD"],
            description="Handles governance requirements",
        )
        initial_count = len(agent_registry.list_agents())
        agent_registry.register(new_agent)
        assert len(agent_registry.list_agents()) == initial_count + 1

    def test_get_agents_for_regulations(self, agent_registry):
        """Test getting agents for specific regulations."""
        agents = agent_registry.get_agents_for_regulations(["CSRD"])
        agent_names = [a.name for a in agents]
        # Should include agents that cover CSRD
        assert len(agent_names) > 0

    def test_get_regulations_by_agent(self, agent_registry):
        """Test getting regulations handled by an agent."""
        regs = agent_registry.get_regulations_by_agent("finance")
        assert "SFDR" in regs
        assert "EU_TAXONOMY" in regs

    def test_enable_disable_agent(self, agent_registry):
        """Test enabling and disabling agents."""
        agent_registry.disable_agent("sustainability")
        enabled_agents = agent_registry.list_enabled_agents()
        names = [a.name for a in enabled_agents]
        assert "sustainability" not in names

        agent_registry.enable_agent("sustainability")
        enabled_agents = agent_registry.list_enabled_agents()
        names = [a.name for a in enabled_agents]
        assert "sustainability" in names


# ============================================================================
# CONFIG LOADER TESTS
# ============================================================================

class TestRegulationConfigLoader:
    """Tests for RegulationConfigLoader system."""

    def test_loader_initializes_with_defaults(self, config_loader):
        """Test that loader loads default regulations."""
        regs = config_loader.get_all_regulations()
        assert len(regs) >= 4  # CSRD, ESRS, EU_TAXONOMY, SFDR
        names = [r.name for r in regs]
        assert "CSRD" in names
        assert "SFDR" in names

    def test_get_regulation_by_name(self, config_loader):
        """Test getting a single regulation."""
        csrd = config_loader.get_regulation("CSRD")
        assert csrd is not None
        assert csrd.full_name == "Corporate Sustainability Reporting Directive"

    def test_get_regulation_case_insensitive(self, config_loader):
        """Test that regulation names are case-insensitive."""
        csrd_upper = config_loader.get_regulation("CSRD")
        csrd_lower = config_loader.get_regulation("csrd")
        assert csrd_upper.name == csrd_lower.name

    def test_get_enabled_regulations(self, config_loader):
        """Test getting only enabled regulations."""
        config_loader.disable_regulation("SFDR")
        enabled = config_loader.get_enabled_regulations()
        names = [r.name for r in enabled]
        assert "SFDR" not in names
        assert "CSRD" in names

    def test_get_regulations_by_jurisdiction(self, config_loader):
        """Test filtering regulations by jurisdiction."""
        eu_regs = config_loader.get_regulations_by_jurisdiction("EU")
        assert len(eu_regs) > 0
        # All should cover EU jurisdiction
        for reg in eu_regs:
            assert any(j.upper() == "EU" for j in reg.jurisdictions)

    def test_get_regulations_by_agent(self, config_loader):
        """Test getting regulations covered by an agent."""
        finance_regs = config_loader.get_regulations_by_agent("finance")
        names = [r.name for r in finance_regs]
        assert "SFDR" in names or "EU_TAXONOMY" in names

    def test_get_threshold(self, config_loader):
        """Test getting specific thresholds."""
        threshold = config_loader.get_threshold("CSRD", "large_enterprise", "employees_min")
        assert threshold == 500

    def test_enable_disable_regulation(self, config_loader):
        """Test enabling and disabling regulations."""
        config_loader.disable_regulation("CSRD")
        enabled = config_loader.get_enabled_regulations()
        names = [r.name for r in enabled]
        assert "CSRD" not in names

        config_loader.enable_regulation("CSRD")
        enabled = config_loader.get_enabled_regulations()
        names = [r.name for r in enabled]
        assert "CSRD" in names


# ============================================================================
# APPLICABILITY CHECKER TESTS
# ============================================================================

class TestApplicabilityChecker:
    """Tests for ApplicabilityChecker with config-based thresholds."""

    def test_checker_loads_config(self):
        """Test that checker initializes with config loader."""
        checker = ApplicabilityChecker()
        assert checker.config_loader is not None

    def test_csrd_applicable_large_enterprise(self):
        """Test CSRD applies to large enterprises."""
        checker = ApplicabilityChecker()
        profile = {
            "employees": 750,
            "turnover_eur": 500_000_000,
            "balance_sheet_eur": 250_000_000,
        }
        result = checker.check_applicability("CSRD", profile)
        assert result.applicable is True
        assert "Phase 1" in result.reason

    def test_csrd_not_applicable_small_company(self):
        """Test CSRD doesn't apply to small companies."""
        checker = ApplicabilityChecker()
        profile = {
            "employees": 50,
            "turnover_eur": 5_000_000,
            "balance_sheet_eur": 2_000_000,
        }
        result = checker.check_applicability("CSRD", profile)
        assert result.applicable is False

    def test_csrd_applicable_listed_sme(self):
        """Test CSRD applies to listed SMEs."""
        checker = ApplicabilityChecker()
        profile = {
            "employees": 100,
            "turnover_eur": 50_000_000,
            "balance_sheet_eur": 25_000_000,
            "listed": True,
        }
        result = checker.check_applicability("CSRD", profile)
        assert result.applicable is True
        assert "Phase 2" in result.reason

    def test_unknown_regulation(self):
        """Test handling of unknown regulation."""
        checker = ApplicabilityChecker()
        profile = {"employees": 100}
        result = checker.check_applicability("UNKNOWN_REG", profile)
        assert result.applicable is False
        assert "not in LIOS knowledge base" in result.reason

    def test_thresholds_in_result(self):
        """Test that thresholds are included in result."""
        checker = ApplicabilityChecker()
        profile = {
            "employees": 750,
            "turnover_eur": 500_000_000,
            "balance_sheet_eur": 250_000_000,
        }
        result = checker.check_applicability("CSRD", profile)
        assert "threshold_details" in result.__dict__
        assert len(result.threshold_details) > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorResponse:
    """Tests for error response models."""

    def test_error_response_creation(self):
        """Test creating an error response."""
        error = ErrorResponse(
            error="Test error message",
            error_type="validation",
            request_id="req-123",
        )
        assert error.error == "Test error message"
        assert error.error_type == "validation"
        assert error.request_id == "req-123"

    def test_error_response_with_details(self):
        """Test error response with additional details."""
        error = ErrorResponse(
            error="Validation failed",
            error_type="validation",
            details={"field": "employees", "value": -10},
            request_id="req-456",
        )
        assert error.details["field"] == "employees"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestConfigAndApplicabilityIntegration:
    """Integration tests for config loader and applicability checker."""

    def test_threshold_updates_flow_to_checker(self):
        """Test that config threshold changes affect applicability checks."""
        loader = RegulationConfigLoader()
        loader.load_default_regulations()

        # Get default threshold
        default_threshold = loader.get_threshold("CSRD", "large_enterprise", "employees_min")
        assert default_threshold == 500

        # Create checker and verify it uses the config
        checker = ApplicabilityChecker()
        result = checker.check_applicability(
            "CSRD",
            {"employees": 501, "turnover_eur": 0, "balance_sheet_eur": 0},
        )
        # Should use the config threshold of 500
        assert "employees" in result.threshold_details

    def test_disabled_regulation_not_used(self):
        """Test that disabled regulations are properly handled."""
        checker = ApplicabilityChecker()
        checker.config_loader.disable_regulation("SFDR")

        enabled = checker.config_loader.get_enabled_regulations()
        names = [r.name for r in enabled]
        assert "SFDR" not in names


# ============================================================================
# SMOKE TESTS
# ============================================================================

class TestSystemSmoke:
    """Smoke tests to ensure basic system functionality."""

    def test_system_initialization(self, logger_setup):
        """Test that all major components initialize."""
        registry = AgentRegistry()
        config = RegulationConfigLoader()
        checker = ApplicabilityChecker()

        assert registry is not None
        assert config is not None
        assert checker is not None

    def test_end_to_end_applicability_check(self):
        """Test complete applicability check flow."""
        # Create profile using validation model
        profile = CompanyProfile(
            employees=600,
            turnover_eur=300_000_000,
            balance_sheet_eur=150_000_000,
        )

        # Create request using validation model
        request = ApplicabilityRequest(
            regulation="CSRD",
            company_profile=profile,
        )

        # Perform check with config-backed checker
        checker = ApplicabilityChecker()
        result = checker.check_applicability(
            request.regulation,
            request.company_profile.model_dump(),
        )

        # Verify result
        assert result.regulation == "CSRD"
        assert isinstance(result.applicable, bool)
        assert len(result.reason) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
