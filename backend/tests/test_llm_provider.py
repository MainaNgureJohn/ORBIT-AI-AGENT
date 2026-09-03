from app.config.settings import Settings
from app.services.llm_provider import OpenAICompatibleExplanationProvider, create_explanation_provider_from_settings


class _SuccessfulResponse:
    def __init__(self, body: dict) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body


def test_groq_provider_uses_chat_completions(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _SuccessfulResponse({"choices": [{"message": {"content": "Grounded guidance"}}]})

    monkeypatch.setattr("app.services.llm_provider.httpx.post", fake_post)
    provider = OpenAICompatibleExplanationProvider(
        api_key="fake-test-key",
        model="openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        provider_name="groq",
    )

    assert provider._request_text("validated context") == "Grounded guidance"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["json"]["messages"] == [{"role": "user", "content": "validated context"}]
    assert provider.last_call_succeeded is True


def test_openai_provider_uses_responses_api(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _SuccessfulResponse({"output_text": "Grounded explanation"})

    monkeypatch.setattr("app.services.llm_provider.httpx.post", fake_post)
    provider = OpenAICompatibleExplanationProvider(api_key="fake-test-key", model="gpt-4.1-mini")

    assert provider._request_text("validated report") == "Grounded explanation"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["json"] == {"model": "gpt-4.1-mini", "input": "validated report", "store": False}


def test_factory_preserves_groq_provider_identity() -> None:
    provider = create_explanation_provider_from_settings(Settings(llm_provider="groq", groq_api_key="fake-test-key"))

    assert isinstance(provider, OpenAICompatibleExplanationProvider)
    assert provider.provider_name == "groq"
    assert provider.model == "openai/gpt-oss-20b"
