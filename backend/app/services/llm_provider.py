"""Provider-neutral explanations with a safe deterministic fallback."""

import json
import httpx
from typing import Protocol

from app.models.schemas import AnalysisReport


class ExplanationProvider(Protocol):
    def generate_explanation(self, report: AnalysisReport) -> str:
        """Turn validated metrics into user-facing explanation text."""


class DeterministicExplanationProvider:
    """Safe fallback that never invents data or requires an LLM credential."""

    provider_name = "deterministic"

    def generate_explanation(self, report: AnalysisReport) -> str:
        score = report.score.final
        risk = report.risk_level.value.lower()
        lead_reason = report.reasons[0] if report.reasons else "No supporting signal was available."
        limitation = report.limitations[0] if report.limitations else "Data limitations apply."
        return f"{report.asset} has an informational opportunity score of {score}/100 with {risk} risk. {lead_reason}. Caution: {limitation}."


class DisabledLLMProvider(DeterministicExplanationProvider):
    """Explicitly named provider used when LLM generation is disabled."""


class OpenAICompatibleExplanationProvider(DeterministicExplanationProvider):
    """Live OpenAI-compatible Responses API provider; failures fall back safely."""

    def __init__(self, *, api_key: str, model: str = "gpt-5-mini", base_url: str = "https://api.openai.com/v1", timeout_seconds: float = 20.0, provider_name: str = "openai") -> None:
        if not api_key.strip():
            raise ValueError("An API key is required for the configured LLM provider")
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.provider_name = provider_name
        self.timeout = timeout_seconds
        self.last_call_succeeded: bool | None = None
        self.last_error_code: str | None = None

    def generate_explanation(self, report: AnalysisReport) -> str:
        prompt = self._request_text(
            "Give a detailed, evidence-based crypto market explanation for this validated report. Use three short sections: What the data says, What to improve or monitor, and Limitations. Include at least three concrete, prioritized observations, but do not invent historical, on-chain, news, or trading data. Do not give buy/sell instructions. Mention the stated limitations.\n"
            + json.dumps(report.model_dump(mode="json"), separators=(",", ":"))
        )
        return prompt or super().generate_explanation(report)

    def generate_advice(self, question: str, context: dict) -> str:
        text = self._request_text(
            "You are ORBIT, a read-only crypto portfolio analyst. Answer the user's improvement question in a detailed response with: (1) a brief assessment, (2) at least three prioritized improvement actions with reasoning, and (3) risks and data limitations. Ground every claim only in the supplied account and public market data. Never claim certainty, invent missing prices, or suggest placing orders. Clearly separate facts, risks, and limitations.\nUser question: "
            + question[:2000]
            + "\nValidated context:\n"
            + json.dumps(context, separators=(",", ":"))
        )
        return text or "The live language model was unavailable; review the deterministic portfolio coverage and risk fields shown above."

    def _request_text(self, input_text: str) -> str:
        # Groq's broadly available OpenAI-compatible surface is Chat Completions.
        # Its Responses API is beta and can return 404 for otherwise valid keys,
        # so use the stable endpoint for Groq while retaining Responses for OpenAI.
        if self.provider_name == "groq":
            endpoint = f"{self.base_url}/chat/completions"
            payload = {"model": self.model, "messages": [{"role": "user", "content": input_text}]}
        else:
            endpoint = f"{self.base_url}/responses"
            payload = {"model": self.model, "input": input_text, "store": False}
        try:
            response = httpx.post(endpoint, headers=self._headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            body = response.json()
            if self.provider_name == "groq":
                output = (((body.get("choices") or [{}])[0]).get("message") or {}).get("content") if isinstance(body, dict) else None
            else:
                output = body.get("output_text") if isinstance(body, dict) else None
            self.last_call_succeeded = isinstance(output, str) and bool(output.strip())
            self.last_error_code = None if self.last_call_succeeded else "EMPTY_RESPONSE"
            return output.strip()[:4000] if isinstance(output, str) else ""
        except httpx.HTTPStatusError as exc:
            self.last_call_succeeded = False
            detail = ""
            try:
                error_body = exc.response.json()
                error = error_body.get("error", {}) if isinstance(error_body, dict) else {}
                message = error.get("message") if isinstance(error, dict) else None
                if isinstance(message, str) and message.strip():
                    detail = ": " + " ".join(message.split())[:160]
            except (ValueError, TypeError):
                pass
            self.last_error_code = f"HTTP_{exc.response.status_code}{detail}"
            return ""
        except (httpx.HTTPError, ValueError, TypeError):
            self.last_call_succeeded = False
            self.last_error_code = "REQUEST_FAILED"
            return ""


def create_explanation_provider_from_settings(settings) -> ExplanationProvider:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAICompatibleExplanationProvider(api_key=settings.openai_api_key, model=settings.openai_model, base_url=settings.openai_base_url, timeout_seconds=settings.llm_timeout_seconds, provider_name="openai")
    if settings.llm_provider == "groq" and settings.groq_api_key:
        return OpenAICompatibleExplanationProvider(api_key=settings.groq_api_key, model=settings.groq_model, base_url=settings.groq_base_url, timeout_seconds=settings.llm_timeout_seconds, provider_name="groq")
    return DisabledLLMProvider()
