"""Tests for new infrastructure improvements:
- Inverted keyword index in RegulatoryDatabase
- Search result caching
- Rate limiting middleware
- Feature base class (BaseFeature)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lios.api.routes import RateLimiter, app, _rate_limiter
from lios.features.base_feature import BaseFeature, FeatureResult
from lios.knowledge.regulatory_db import RegulatoryDatabase


# ---------------------------------------------------------------------------
# RegulatoryDatabase – inverted index and caching
# ---------------------------------------------------------------------------

class TestRegulatoryDatabaseIndex:
    """Tests for the inverted keyword index and search cache."""

    @pytest.fixture
    def db(self):
        return RegulatoryDatabase()

    def test_keyword_index_built_on_init(self, db):
        """Inverted index should be populated after database initialisation."""
        assert len(db._keyword_index) > 0

    def test_keyword_index_contains_known_words(self, db):
        """Common legal keywords should appear in the index."""
        for keyword in ("reporting", "disclosure", "sustainability"):
            assert keyword in db._keyword_index, f"'{keyword}' missing from index"

    def test_search_articles_returns_results(self, db):
        """search_articles should return relevant matches."""
        results = db.search_articles("sustainability reporting")
        assert len(results) > 0

    def test_search_articles_regulation_filter(self, db):
        """Filtering by regulation limits results to that regulation."""
        results = db.search_articles("disclosure reporting", regulation="CSRD")
        for r in results:
            assert r["regulation"] == "CSRD"

    def test_search_articles_sorted_by_relevance(self, db):
        """Results must be sorted in descending relevance order."""
        results = db.search_articles("disclosure reporting requirements sustainability")
        scores = [r["relevance_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_articles_empty_query_returns_empty(self, db):
        """Very short queries (after stop-word filtering) return empty list."""
        results = db.search_articles("a b")  # All tokens <= 2 chars
        assert results == []

    def test_search_cache_is_populated_on_first_call(self, db):
        """After a search the result should be stored in the cache."""
        db._search_cache.clear()
        db.search_articles("climate emissions")
        assert len(db._search_cache) == 1

    def test_search_cache_is_used_on_second_call(self, db):
        """Repeated identical searches should hit the cache."""
        db._search_cache.clear()
        r1 = db.search_articles("climate emissions")
        r2 = db.search_articles("climate emissions")  # should come from cache
        assert r1 == r2
        assert len(db._search_cache) == 1  # still only 1 entry

    def test_search_cache_is_case_normalised(self, db):
        """Cache key should be case-insensitive on the query."""
        db._search_cache.clear()
        r1 = db.search_articles("Climate Emissions")
        r2 = db.search_articles("climate emissions")
        assert r1 == r2
        assert len(db._search_cache) == 1

    def test_search_cache_evicts_lru_entry_when_full(self, db):
        """Cache should not grow beyond _search_cache_max and should evict LRU."""
        db._search_cache.clear()
        original_max = db._search_cache_max
        db._search_cache_max = 3

        # Fill the cache with 3 distinct queries
        db.search_articles("reporting requirements")       # key A (oldest)
        db.search_articles("disclosure sustainability")    # key B
        db.search_articles("climate emissions scope")      # key C (newest)
        assert len(db._search_cache) == 3

        # Re-access key A to make it the most recently used
        db.search_articles("reporting requirements")       # moves A to front

        # Adding a new query should evict key B (now the least recently used)
        db.search_articles("taxonomy alignment activities")  # key D – triggers eviction
        assert len(db._search_cache) == 3

        # Key B should have been evicted (it was LRU); A, C, D should remain
        remaining = set(db._search_cache.keys())
        key_a = db._make_cache_key("reporting requirements", None)
        key_b = db._make_cache_key("disclosure sustainability", None)
        key_c = db._make_cache_key("climate emissions scope", None)
        key_d = db._make_cache_key("taxonomy alignment activities", None)
        assert key_a in remaining     # A – recently accessed
        assert key_b not in remaining  # B – was LRU, evicted
        assert key_c in remaining    # C
        assert key_d in remaining  # D – just inserted

        db._search_cache_max = original_max  # restore

    def test_unknown_regulation_returns_empty(self, db):
        """Filtering by an unknown regulation key should return empty list."""
        results = db.search_articles("reporting", regulation="UNKNOWN_REG_XYZ")
        assert results == []


# ---------------------------------------------------------------------------
# BaseFeature interface
# ---------------------------------------------------------------------------

class TestBaseFeature:
    """Tests for the BaseFeature abstract base class."""

    def test_cannot_instantiate_directly(self):
        """BaseFeature is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseFeature()  # type: ignore[abstract]

    def test_concrete_feature_must_implement_execute(self):
        """Subclass without execute() cannot be instantiated."""
        class IncompleteFeature(BaseFeature):
            feature_type = "incomplete"

        with pytest.raises(TypeError):
            IncompleteFeature()  # type: ignore[abstract]

    def test_concrete_feature_can_be_instantiated(self):
        """Properly implemented subclass should be instantiable."""
        class ConcreteFeature(BaseFeature):
            feature_type = "concrete"

            def execute(self, query, context):
                return FeatureResult(feature_type=self.feature_type, data={"ok": True})

        feat = ConcreteFeature()
        result = feat.execute("test query", {})
        assert result.feature_type == "concrete"
        assert result.data == {"ok": True}

    def test_feature_result_confidence_validation(self):
        """FeatureResult should reject out-of-range confidence."""
        with pytest.raises(ValueError):
            FeatureResult(feature_type="test", data={}, confidence=1.5)

        with pytest.raises(ValueError):
            FeatureResult(feature_type="test", data={}, confidence=-0.1)

    def test_feature_result_defaults(self):
        """FeatureResult should have sensible defaults."""
        r = FeatureResult(feature_type="test", data={"x": 1})
        assert r.confidence == 1.0
        assert r.metadata == {}

    def test_supports_returns_true_by_default(self):
        """Default supports() always returns True."""
        class AnyFeature(BaseFeature):
            feature_type = "any"

            def execute(self, query, context):
                return FeatureResult(feature_type=self.feature_type, data={})

        feat = AnyFeature()
        assert feat.supports("anything", {}) is True


# ---------------------------------------------------------------------------
# Rate limiting middleware
# ---------------------------------------------------------------------------

class TestRateLimiter:
    """Tests for the in-memory sliding-window rate limiter."""

    def test_allows_requests_within_limit(self):
        """Requests within the window should be allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60.0)
        for _ in range(5):
            assert limiter.is_allowed("127.0.0.1") is True

    def test_blocks_requests_over_limit(self):
        """Requests exceeding the window limit should be blocked."""
        limiter = RateLimiter(max_requests=3, window_seconds=60.0)
        for _ in range(3):
            limiter.is_allowed("10.0.0.1")
        assert limiter.is_allowed("10.0.0.1") is False

    def test_different_ips_are_independent(self):
        """Rate limits should be per-IP and not shared."""
        limiter = RateLimiter(max_requests=1, window_seconds=60.0)
        limiter.is_allowed("1.1.1.1")
        # First IP blocked
        assert limiter.is_allowed("1.1.1.1") is False
        # Second IP still allowed
        assert limiter.is_allowed("2.2.2.2") is True

    def test_rate_limit_returns_429_when_exceeded(self):
        """API should return HTTP 429 when rate limit is exceeded."""
        client = TestClient(app, raise_server_exceptions=False)

        # Temporarily lower the global limiter's limit to 1 request
        original_max = _rate_limiter._max
        _rate_limiter._max = 1

        # Determine the IP TestClient uses and clear its hit counter
        test_ip = "testclient"
        _rate_limiter._hits.pop(test_ip, None)

        try:
            # First request should succeed (/regulations is rate-limited)
            client.get("/regulations")
            # Second request should be rate-limited
            response = client.get("/regulations")
            assert response.status_code == 429
            assert "Retry-After" in response.headers
        finally:
            # Always restore original settings
            _rate_limiter._max = original_max
            _rate_limiter._hits.pop(test_ip, None)

    def test_health_endpoint_exempt_from_rate_limit(self):
        """Health endpoint should never be rate-limited."""
        client = TestClient(app, raise_server_exceptions=False)

        original_max = _rate_limiter._max
        _rate_limiter._max = 0  # Block everything

        try:
            response = client.get("/health")
            assert response.status_code == 200  # still works
        finally:
            _rate_limiter._max = original_max
