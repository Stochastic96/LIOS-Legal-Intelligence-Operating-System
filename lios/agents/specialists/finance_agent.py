"""Finance specialist agent – SFDR, MiFID II ESG, EBA guidelines."""

from __future__ import annotations

from lios.agents.base_agent import AgentResponse, BaseAgent

_SYSTEM_PROMPT = """You are a specialist in EU sustainable finance law:
- SFDR (Sustainable Finance Disclosure Regulation 2019/2088)
- EU Taxonomy Regulation (financial product disclosures)
- MiFID II ESG preferences (Delegated Regulation 2021/1253)
- EBA / ESMA / EIOPA ESG guidelines

Given the regulatory context below and the user's question, respond in JSON:

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


class FinanceAgent(BaseAgent):
    """Handles SFDR, MiFID II ESG, and sustainable finance queries."""

    agent_id = "finance"

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
