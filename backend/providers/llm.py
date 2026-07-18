"""Provider LLM sau interface (AD-7, AD-8).

- `LLMProvider` Protocol: `generate(system, prompt) -> str`.
- `MockLLM`: deterministic, KHÔNG gọi mạng — dùng khi không có key (dev/test/đường lui).
- `AnthropicLLM`: gọi Anthropic Messages API thật qua httpx.
- `get_llm()`: chọn provider theo `LLM_API_KEY`. Key chỉ đọc ở backend, không log.
"""

from __future__ import annotations

import os
from typing import Protocol

import httpx

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")
REQUEST_TIMEOUT_S = 15.0


def get_api_key() -> str:
    return os.environ.get("LLM_API_KEY", "")


def is_configured() -> bool:
    return bool(get_api_key())


def _model() -> str:
    # Đọc lúc GỌI (không phải lúc import) — tránh giá trị cũ trước khi load_dotenv.
    return os.environ.get("LLM_MODEL", "claude-sonnet-4-6")


def _base_url() -> str:
    """URL gốc cho provider kiểu OpenAI. Tự đoán DeepSeek nếu model gợi ý."""
    explicit = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    if "deepseek" in _model().lower():
        return "https://api.deepseek.com"
    return "https://api.openai.com/v1"


class LLMProvider(Protocol):
    def generate(self, system: str, prompt: str, timeout: float | None = None) -> str: ...


class MockLLM:
    """Trả câu trả lời tiếng Việt template từ prompt — không mạng, deterministic."""

    def generate(self, system: str, prompt: str, timeout: float | None = None) -> str:
        return (
            "[MockLLM — chạy không cần API key] Dựa trên các điều khoản còn hiệu lực "
            "được cung cấp:\n" + prompt.strip()
        )


class AnthropicLLM:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model

    def generate(self, system: str, prompt: str, timeout: float | None = None) -> str:
        resp = httpx.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": self._model,
                "max_tokens": 1024,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=timeout or REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


class OpenAICompatLLM:
    """Provider tương thích OpenAI (dùng cho OpenAI, DeepSeek, và các API cùng chuẩn)."""

    def __init__(
        self, api_key: str, model: str = DEFAULT_MODEL, base_url: str | None = None
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = (base_url or _base_url()).rstrip("/")

    def generate(self, system: str, prompt: str, timeout: float | None = None) -> str:
        # Chịu được base_url có sẵn '/chat/completions' hay chỉ '/v1'
        url = self._base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "content-type": "application/json",
            },
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=timeout or REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def get_llm() -> LLMProvider:
    if not is_configured():
        return MockLLM()
    model = _model()  # đọc lúc gọi (sau load_dotenv)
    # Claude → Anthropic; còn lại (OpenAI, DeepSeek, FPT, có LLM_BASE_URL) → OpenAI-compat
    use_anthropic = "claude" in model.lower() and not os.environ.get("LLM_BASE_URL")
    if use_anthropic:
        return AnthropicLLM(get_api_key(), model)
    return OpenAICompatLLM(get_api_key(), model)
