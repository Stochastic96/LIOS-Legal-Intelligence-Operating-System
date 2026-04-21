"""Integration tests for /api/synthesize and /api/evaluate endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lios.api.routes import app

client = TestClient(app)


class TestSynthesizeEndpoint:
    def test_synthesize_returns_200(self):
        resp = client.post("/api/synthesize", json={"query": "What is double materiality?"})
        assert resp.status_code == 200

    def test_synthesize_response_has_required_fields(self):
        resp = client.post("/api/synthesize", json={"query": "What is CSRD?"})
        data = resp.json()
        assert "query" in data
        assert "answer" in data
        assert "question_type" in data
        assert "sources" in data

    def test_synthesize_answer_is_nonempty(self):
        resp = client.post("/api/synthesize", json={"query": "What are the CSRD penalties?"})
        data = resp.json()
        assert len(data["answer"]) > 20

    def test_synthesize_question_type_is_valid(self):
        valid_types = {
            "definition", "applicability", "requirement",
            "procedure", "timeline", "comparison", "penalty", "general",
        }
        resp = client.post(
            "/api/synthesize",
            json={"query": "When does CSRD apply?"},
        )
        data = resp.json()
        assert data["question_type"] in valid_types

    def test_synthesize_query_echoed(self):
        question = "What is the CSRD reporting deadline?"
        resp = client.post("/api/synthesize", json={"query": question})
        assert resp.json()["query"] == question

    def test_synthesize_sources_is_list(self):
        resp = client.post("/api/synthesize", json={"query": "What is CSRD?"})
        assert isinstance(resp.json()["sources"], list)

    def test_synthesize_irac_structure_in_answer(self):
        resp = client.post("/api/synthesize", json={"query": "What is double materiality?"})
        answer = resp.json()["answer"]
        # Synthesizer builds IRAC answers
        assert "**Issue:**" in answer or "Issue" in answer

    def test_synthesize_different_questions_produce_different_answers(self):
        resp1 = client.post("/api/synthesize", json={"query": "What are the CSRD penalties?"})
        resp2 = client.post("/api/synthesize", json={"query": "When does CSRD apply?"})
        assert resp1.json()["answer"] != resp2.json()["answer"]


class TestEvaluateEndpoint:
    def test_evaluate_returns_200(self):
        resp = client.post(
            "/api/evaluate",
            json={
                "question": "What are the CSRD penalties?",
                "answer": "CSRD Art.7 requires penalties that are effective and dissuasive.",
            },
        )
        assert resp.status_code == 200

    def test_evaluate_response_has_required_fields(self):
        resp = client.post(
            "/api/evaluate",
            json={
                "question": "What is CSRD?",
                "answer": "CSRD is the Corporate Sustainability Reporting Directive.",
            },
        )
        data = resp.json()
        for field in (
            "question", "overall_score", "grade", "grounding_score",
            "citation_score", "completeness_score", "diversity_score", "feedback",
        ):
            assert field in data

    def test_evaluate_scores_in_range(self):
        resp = client.post(
            "/api/evaluate",
            json={
                "question": "What are the requirements?",
                "answer": "Companies shall disclose sustainability information under CSRD.",
            },
        )
        data = resp.json()
        for key in ("overall_score", "grounding_score", "citation_score",
                    "completeness_score", "diversity_score"):
            assert 0.0 <= data[key] <= 1.0

    def test_evaluate_grade_is_letter(self):
        resp = client.post(
            "/api/evaluate",
            json={"question": "What is CSRD?", "answer": "CSRD is a directive."},
        )
        assert resp.json()["grade"] in {"A", "B", "C", "D", "F"}

    def test_evaluate_feedback_is_list(self):
        resp = client.post(
            "/api/evaluate",
            json={"question": "What is CSRD?", "answer": "Some answer."},
        )
        assert isinstance(resp.json()["feedback"], list)

    def test_evaluate_question_echoed(self):
        q = "What are the penalties for non-compliance?"
        resp = client.post(
            "/api/evaluate",
            json={"question": q, "answer": "CSRD Art.7 penalties apply."},
        )
        assert resp.json()["question"] == q
