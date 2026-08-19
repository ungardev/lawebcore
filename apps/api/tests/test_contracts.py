"""Level 1 — Contract tests: schemas, enums, types.

Tests que validan que los schemas y tipos son correctos.
No requieren DB ni APIs externas.
"""

import pytest
from discovery.schemas import (
    BriefStructured,
    CandidateStatus,
    DiscoveryRunStatus,
    DiscoverySearchRequest,
    Platform,
)


class TestDiscoveryRunStatusEnum:
    """Valida que DiscoveryRunStatus tenga todos los valores esperados."""

    def test_has_pending(self):
        assert "pending" in [s.value for s in DiscoveryRunStatus]

    def test_has_running(self):
        assert "running" in [s.value for s in DiscoveryRunStatus]

    def test_has_completed(self):
        assert "completed" in [s.value for s in DiscoveryRunStatus]

    def test_has_failed(self):
        assert "failed" in [s.value for s in DiscoveryRunStatus]

    def test_has_cancelled(self):
        assert "cancelled" in [s.value for s in DiscoveryRunStatus]

    def test_has_partial(self):
        assert "partial" in [s.value for s in DiscoveryRunStatus]

    def test_has_explored(self):
        assert "explored" in [s.value for s in DiscoveryRunStatus]


class TestBriefStructuredFields:
    """Valida que BriefStructured tenga los campos de modo Explorar/Analizar."""

    def test_has_discovery_mode_field(self):
        brief = BriefStructured()
        assert hasattr(brief, "discovery_mode")
        assert brief.discovery_mode == "auto"

    def test_discovery_mode_default_is_auto(self):
        brief = BriefStructured()
        assert brief.discovery_mode == "auto"

    def test_discovery_mode_can_be_explore(self):
        brief = BriefStructured(discovery_mode="explore")
        assert brief.discovery_mode == "explore"

    def test_discovery_mode_can_be_analyze(self):
        brief = BriefStructured(discovery_mode="analyze")
        assert brief.discovery_mode == "analyze"

    def test_has_handles_to_analyze_field(self):
        brief = BriefStructured()
        assert hasattr(brief, "handles_to_analyze")
        assert brief.handles_to_analyze == []

    def test_handles_to_analyze_accepts_list(self):
        brief = BriefStructured(handles_to_analyze=["handle1", "handle2"])
        assert brief.handles_to_analyze == ["handle1", "handle2"]

    def test_has_parent_run_id_field(self):
        brief = BriefStructured()
        assert hasattr(brief, "parent_run_id")
        assert brief.parent_run_id is None

    def test_parent_run_id_accepts_string(self):
        brief = BriefStructured(parent_run_id="abc-123")
        assert brief.parent_run_id == "abc-123"

    def test_has_exclude_handles_field(self):
        brief = BriefStructured(exclude_handles=["blocked_handle"])
        assert brief.exclude_handles == ["blocked_handle"]


class TestDiscoverySearchRequestFields:
    """Valida DiscoverySearchRequest para API requests."""

    def test_has_discovery_mode(self):
        req = DiscoverySearchRequest()
        assert hasattr(req, "discovery_mode")
        assert req.discovery_mode == "auto"

    def test_discovery_mode_explore(self):
        req = DiscoverySearchRequest(discovery_mode="explore")
        assert req.discovery_mode == "explore"

    def test_discovery_mode_analyze(self):
        req = DiscoverySearchRequest(discovery_mode="analyze")
        assert req.discovery_mode == "analyze"

    def test_has_handles_to_analyze(self):
        req = DiscoverySearchRequest(handles_to_analyze=["@test_handle"])
        assert req.handles_to_analyze == ["@test_handle"]

    def test_handles_to_analyze_empty_by_default(self):
        req = DiscoverySearchRequest()
        assert req.handles_to_analyze == []


class TestCandidateStatusEnum:
    """Valida CandidateStatus enum."""

    def test_has_new(self):
        assert "new" in [s.value for s in CandidateStatus]

    def test_has_saved(self):
        assert "saved" in [s.value for s in CandidateStatus]

    def test_has_dismissed(self):
        assert "dismissed" in [s.value for s in CandidateStatus]


class TestPlatformEnum:
    """Valida Platform enum."""

    def test_has_instagram(self):
        assert "instagram" in [p.value for p in Platform]

    def test_has_tiktok(self):
        assert "tiktok" in [p.value for p in Platform]

    def test_has_youtube(self):
        assert "youtube" in [p.value for p in Platform]
