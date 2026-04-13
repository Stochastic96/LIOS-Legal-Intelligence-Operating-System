"""Sustainability specialist agent – CSRD, ESRS, EU Taxonomy."""

from __future__ import annotations

from lios.agents.base_agent import AgentResponse, BaseAgent

_SYSTEM_PROMPT = """You are a specialist in EU sustainability law, specifically:
- CSRD (Corporate Sustainability Reporting Directive 2022/2464)
- ESRS (European Sustainability Reporting Standards)
- EU Taxonomy Regulation (2020/852)
- CSDDD (Corporate Sustainability Due Diligence Directive 2024/1760)

Given the regulatory context below and the user's question, provide a precise,
citation-grounded answer in JSON format:

{{
  "answer": "<concise legal answer>",
  "citations": [
    {{"regulation": "<short name>", "article": "<Art. X>", "excerpt": "<quoted text>"}}
  ],
  "confidence": <0.0-1.0>,
  "reasoning": "<chain of thought>"
}}

Regulatory context:
{context}

User question: {query}
"""


class SustainabilityAgent(BaseAgent):
    """Handles CSRD / ESRS / EU Taxonomy / CSDDD queries."""

    agent_id = "sustainability"

    async def respond(self, query: str, context_chunks: list[str]) -> AgentResponse:
        prompt = _SYSTEM_PROMPT.format(
            context=self._format_context(context_chunks),
            query=query,
        )
        raw = await self._call_llm(prompt)
        parsed = self._parse_json_response(raw)

        return AgentResponse(
            agent_id=self.agent_id,
            answer=parsed.get("answer", raw),
            citations=parsed.get("citations", []),
            confidence=float(parsed.get("confidence", 0.8)),
            reasoning=parsed.get("reasoning", ""),
        )
