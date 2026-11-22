from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
import os
import time
from typing import Any
import urllib.error
import urllib.request

logger = logging.getLogger("biobangla.ai")


class AIProviderError(RuntimeError):
    """Raised when an AI provider is misconfigured or returns an invalid response."""


class AIProvider(ABC):
    """Provider-independent interface for structured Bangla scientific journalism generation."""

    provider_name: str = "abstract"
    model_name: str = "unspecified"
    is_mock: bool = False

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate a structured JSON object following the editorial schema."""
        raise NotImplementedError


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIProviderError("AI response did not contain a valid JSON object.")
    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise AIProviderError("Expected top-level JSON object from AI provider.")
    return parsed


def _post_json_with_retries(
    url: str,
    body_dict: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 120,
    max_retries: int = 3,
) -> dict[str, Any]:
    data = json.dumps(body_dict).encode("utf-8")
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                delay = 5.0 * (2**attempt)
                logger.warning(
                    "Transient AI HTTP %d (attempt %d/%d); retrying in %.1fs...",
                    exc.code,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            raise AIProviderError(
                f"AI HTTP {exc.code}: {err_body or exc.reason}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < max_retries:
                delay = 4.0 * (2**attempt)
                time.sleep(delay)
                continue
            raise AIProviderError(f"AI network timeout/error: {exc}") from exc
    raise AIProviderError("Exhausted AI request retries.")


class OpenAICompatibleProvider(AIProvider):
    """Supports OpenAI, Groq, OpenRouter, and any OpenAI-compatible Chat Completions endpoint."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.2,
        timeout: int = 120,
    ) -> None:
        if not api_key:
            raise AIProviderError("AI_API_KEY is required for OpenAI-compatible provider.")
        self.api_key = api_key
        self.model_name = model or "gpt-4o-mini"
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload = _post_json_with_retries(
            url=url,
            body_dict={
                "model": self.model_name,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        content = payload["choices"][0]["message"]["content"]
        return _extract_json_object(content)


class GeminiProvider(AIProvider):
    """Official Google Gemini Developer REST API provider (supports both AIza... and AQ.... keys)."""

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash",
        temperature: float = 0.2,
        timeout: int = 60,
    ) -> None:
        if not api_key:
            raise AIProviderError("AI_API_KEY is required for Gemini provider.")
        self.api_key = api_key
        self.model_name = model or "gemini-3.5-flash"
        self.temperature = temperature
        self.timeout = timeout

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        models_to_try: list[str] = []
        for m in (
            self.model_name,
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
            "gemini-3.6-flash",
        ):
            if m and m not in models_to_try:
                models_to_try.append(m)

        last_err: Exception | None = None
        for idx, candidate_model in enumerate(models_to_try):
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{candidate_model}:generateContent"
            )
            try:
                payload = _post_json_with_retries(
                    url=url,
                    body_dict={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        "generationConfig": {
                            "temperature": self.temperature,
                            "responseMimeType": "application/json",
                        },
                    },
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key,
                    },
                    timeout=self.timeout,
                    max_retries=1,
                )
                self.model_name = candidate_model
                text = payload["candidates"][0]["content"]["parts"][0]["text"]
                return _extract_json_object(text)
            except AIProviderError as exc:
                last_err = exc
                err_str = str(exc)
                is_recoverable = any(
                    token in err_str
                    for token in (
                        "HTTP 404",
                        "HTTP 429",
                        "HTTP 500",
                        "HTTP 502",
                        "HTTP 503",
                        "HTTP 504",
                        "timeout",
                        "no longer available",
                        "high demand",
                    )
                )
                if is_recoverable and idx < len(models_to_try) - 1:
                    logger.warning(
                        "Model %s unavailable/busy (%s); failing over to %s",
                        candidate_model,
                        err_str[:120],
                        models_to_try[idx + 1],
                    )
                    continue
                raise
        raise AIProviderError(str(last_err))


class AnthropicProvider(AIProvider):
    """Official Anthropic Messages REST API provider."""

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-latest",
        temperature: float = 0.2,
        timeout: int = 120,
    ) -> None:
        if not api_key:
            raise AIProviderError("AI_API_KEY is required for Anthropic provider.")
        self.api_key = api_key
        self.model_name = model or "claude-3-5-haiku-latest"
        self.temperature = temperature
        self.timeout = timeout

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        payload = _post_json_with_retries(
            url=url,
            body_dict={
                "model": self.model_name,
                "max_tokens": 4096,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        text = payload["content"][0]["text"]
        return _extract_json_object(text)


class MockJournalismProvider(AIProvider):
    """
    Deterministic offline provider for local tests & dry-run verification ONLY.
    Never claims external AI connectivity; always marks output with mock provenance.
    """

    provider_name = "mock"
    model_name = "offline-deterministic-template-v1"
    is_mock = True

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        meta = _extract_json_object(user_prompt)
        title_en = str(meta.get("title", "Biological Study"))
        journal = str(meta.get("journal", "Scientific Journal"))
        doi = meta.get("doi") or ""
        is_preprint = not bool(meta.get("peer_reviewed", True))
        study_model = str(meta.get("study_model", "multi-study"))

        preprint_prefix = "প্রিপ্রিন্ট বিশ্লেষণ: " if is_preprint else ""
        preprint_note = (
            "এই গবেষণাটি একটি প্রিপ্রিন্ট সার্ভারে প্রকাশিত প্রাথমিক পাণ্ডুলিপি এবং এখনো আনুষ্ঠানিক পিয়ার-রিভিউ সম্পন্ন করেনি। "
            if is_preprint
            else f"এই গবেষণাটি {journal} জার্নালে পিয়ার-রিভিউ প্রক্রিয়ায় প্রকাশিত হয়েছে। "
        )

        body = f"""## গবেষণার প্রেক্ষাপট

জীববিজ্ঞান ও আণবিক গবেষণার সমসাময়িক ধারায় **{title_en}** শীর্ষক গবেষণাটি একটি গুরুত্বপূর্ণ বৈজ্ঞানিক প্রশ্ন সামনে এনেছে। {preprint_note}গবেষকেরা মূলত সংশ্লিষ্ট জৈবিক প্রক্রিয়ার আণবিক ও পরিবেশগত ভিত্তি নির্ণয় করতে চেয়েছেন, যাতে পূর্ববর্তী জ্ঞানের সীমাবদ্ধতা অতিক্রম করা যায় এবং ভবিষ্যৎ গবেষণার পথ সুগম হয়।

## গবেষণা পদ্ধতি

এই গবেষণায় ব্যবহৃত প্রধান পরীক্ষামূলক কাঠামো ছিল **{study_model}** পর্যায়ের সুশৃঙ্খল বিশ্লেষণ। গবেষক দল নিয়ন্ত্রিত নমুনা সংগ্রহ, পরিমাণগত পরিমাপ এবং পরিসংখ্যানগত যাচাইকরণের মাধ্যমে প্রতিটি চলকের প্রভাব পরীক্ষা করেছেন। গবেষণাপত্রের মূল শনাক্তকারী সূত্র {f'DOI: `{doi}`' if doi else journal} অনুযায়ী সকল পদ্ধতিগত ধাপ বিস্তারিতভাবে নথিভুক্ত করা হয়েছে।

## প্রধান ফলাফল

উপাত্ত বিশ্লেষণে দেখা গেছে যে পরীক্ষিত জৈবিক উপাদানগুলোর মধ্যে সুনির্দিষ্ট কাঠামোগত ও কার্যকরী সম্পর্ক বিদ্যমান। নিয়ন্ত্রিত গ্রুপের তুলনায় পরীক্ষামূলক নমুনায় পরিমাপযোগ্য পরিবর্তন লক্ষ্য করা গেছে, যা লেখকদের প্রাথমিক বৈজ্ঞানিক অনুমানকে সমর্থন করে। তবে পর্যবেক্ষণমূলক সহসম্পর্ক এবং প্রত্যক্ষ কার্যকারণ সম্পর্কের পার্থক্য বজায় রেখেই ফলাফলগুলো সতর্কতার সাথে ব্যাখ্যা করা হয়েছে।

## বৈজ্ঞানিক গুরুত্ব

সংশ্লিষ্ট জীববিজ্ঞান শাখায় এই ফলাফল ভবিষ্যৎ মৌলিক গবেষণা ও পদ্ধতিগত উন্নয়নে সহায়ক তথ্যভাণ্ডার হিসেবে কাজ করবে। অন্যান্য স্বাধীন গবেষণাগারে এই ফলাফল পুনরুৎপাদিত হলে বিষয়টির তাত্ত্বিক ও ব্যবহারিক ভিত্তি আরও সুদৃঢ় হবে।

## সীমাবদ্ধতা ও সতর্কতা

প্রতিটি বৈজ্ঞানিক গবেষণার মতোই এই সমীক্ষার নির্দিষ্ট নমুনা আকার ও পরীক্ষামূলক পরিবেশগত সীমাবদ্ধতা রয়েছে। {preprint_note}এই বাংলা সারসংক্ষেপটি শুধুমাত্র শিক্ষামূলক উদ্দেশ্যে প্রস্তুত; এটি কোনো চিকিৎসা পরামর্শ বা ক্লিনিক্যাল নির্দেশনা নয়।"""

        return {
            "title_bn": f"{preprint_prefix}{journal}-এ প্রকাশিত জৈবিক গবেষণার বাংলা বিশ্লেষণ ({title_en[:55]})",
            "description_bn": f"{journal}-এ প্রকাশিত '{title_en[:70]}' শীর্ষক গবেষণাপত্রের প্রেক্ষাপট, পদ্ধতি, প্রধান ফলাফল ও বৈজ্ঞানিক সীমাবদ্ধতার সহজ বাংলা ব্যাখ্যা।",
            "tags_bn": ["জীববিজ্ঞান", "গবেষণা বিশ্লেষণ", "প্রিপ্রিন্ট" if is_preprint else "পিয়ার-রিভিউকৃত"],
            "key_findings_bn": [
                f"মূল গবেষণাপত্রটি {journal} উৎস থেকে সংগৃহীত ({'প্রিপ্রিন্ট — অ-পর্যালোচিত' if is_preprint else 'পিয়ার-রিভিউকৃত'})।",
                f"গবেষণার পরীক্ষামূলক মডেল: {study_model}।",
            ],
            "body_markdown_bn": body,
        }


def _infer_provider_from_key(api_key: str) -> tuple[str, str, str]:
    """Infers (provider_kind, default_model, default_base_url) from common API key prefixes."""
    if api_key.startswith("AIza") or api_key.startswith("AQ."):
        return ("gemini", "gemini-3.5-flash", "")
    if api_key.startswith("sk-ant-"):
        return ("anthropic", "claude-3-5-haiku-latest", "")
    if api_key.startswith("gsk_"):
        return ("openai_compatible", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1")
    if api_key.startswith("sk-or-"):
        return ("openai_compatible", "google/gemini-2.5-flash", "https://openrouter.ai/api/v1")
    return ("openai", "gpt-4o-mini", "https://api.openai.com/v1")


def create_ai_provider_from_env() -> AIProvider:
    raw_provider = os.getenv("AI_PROVIDER", "").strip().lower()
    api_key = (
        os.getenv("AI_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "").strip()
        or os.getenv("GROQ_API_KEY", "").strip()
    )
    model = os.getenv("AI_MODEL", "").strip()
    base_url = os.getenv("AI_BASE_URL", "").strip()
    temperature = float(os.getenv("AI_TEMPERATURE", "0.2"))

    # If AI_PROVIDER was Explicitly set to "mock" AND no API key is provided, use Mock
    if raw_provider == "mock" and not api_key:
        logger.warning(
            "AI_PROVIDER is 'mock' and no AI_API_KEY is configured. "
            "Drafts will be held in state/review_queue/ and NOT published live."
        )
        return MockJournalismProvider()

    # If neither AI_PROVIDER nor AI_API_KEY is set, fall back safely to Mock
    if not raw_provider and not api_key:
        logger.warning(
            "No AI_API_KEY found in environment/GitHub Secrets! Falling back to 'mock' provider "
            "(articles will be held in REVIEW queue until AI_API_KEY is added to GitHub Secrets)."
        )
        return MockJournalismProvider()

    # If AI_API_KEY IS set, auto-detect provider when AI_PROVIDER wasn't explicitly set (or left blank)
    if api_key and raw_provider in ("", "auto"):
        inferred_kind, inferred_model, inferred_base = _infer_provider_from_key(api_key)
        provider_kind = inferred_kind
        model = model or inferred_model
        base_url = base_url or inferred_base
        logger.info("Auto-detected AI provider '%s' from API key prefix.", provider_kind)
    else:
        provider_kind = raw_provider

    if provider_kind == "mock":
        return MockJournalismProvider()
    if provider_kind in ("openai", "openai_compatible"):
        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            base_url=base_url or "https://api.openai.com/v1",
            temperature=temperature,
        )
    if provider_kind == "gemini":
        return GeminiProvider(
            api_key=api_key,
            model=model or "gemini-3.5-flash",
            temperature=temperature,
        )
    if provider_kind == "anthropic":
        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-3-5-haiku-latest",
            temperature=temperature,
        )
    raise AIProviderError(
        f"Unsupported AI_PROVIDER='{provider_kind}'. Choose mock, gemini, openai, openai_compatible, or anthropic."
    )
