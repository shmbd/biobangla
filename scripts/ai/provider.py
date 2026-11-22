from __future__ import annotations

from abc import ABC, abstractmethod
import json
import os
from typing import Any
import urllib.request


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


class OpenAICompatibleProvider(AIProvider):
    """Supports OpenAI and any OpenAI-compatible Chat Completions endpoint."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.2,
        timeout: int = 60,
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
        body = json.dumps(
            {
                "model": self.model_name,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        return _extract_json_object(content)


class GeminiProvider(AIProvider):
    """Official Google Gemini REST API provider."""

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.2,
        timeout: int = 60,
    ) -> None:
        if not api_key:
            raise AIProviderError("AI_API_KEY is required for Gemini provider.")
        self.api_key = api_key
        self.model_name = model or "gemini-2.5-flash"
        self.temperature = temperature
        self.timeout = timeout

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": self.temperature,
                    "responseMimeType": "application/json",
                },
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json_object(text)


class AnthropicProvider(AIProvider):
    """Official Anthropic Messages REST API provider."""

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-latest",
        temperature: float = 0.2,
        timeout: int = 60,
    ) -> None:
        if not api_key:
            raise AIProviderError("AI_API_KEY is required for Anthropic provider.")
        self.api_key = api_key
        self.model_name = model or "claude-3-5-haiku-latest"
        self.temperature = temperature
        self.timeout = timeout

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        body = json.dumps(
            {
                "model": self.model_name,
                "max_tokens": 4096,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
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

জীববিজ্ঞান ও আণবিক গবেষণার সমসাময়িক ধারায় **{title_en}** শীর্ষক গবেষণাটি একটি গুরুত্বপূর্ণ বৈজ্ঞানিক প্রশ্ন সামনে এনেছে। {preprint_note}গবেষকেরা মূলত সংশ্লিষ্ট জৈবিক প্রক্রিয়ার আণবিক ও পরিবেশগত ভিত্তি নির্ণয় করতে চেয়েছেন, যাতে পূর্ববর্তী জ্ঞানের সীমাবদ্ধতা অতিক্রম করা যায়।

## গবেষণা পদ্ধতি

এই গবেষণায় ব্যবহৃত প্রধান পরীক্ষামূলক কাঠামো ছিল **{study_model}** পর্যায়ের বিশ্লেষণ। গবেষক দল নিয়ন্ত্রিত নমুনা সংগ্রহ, পরিমাণগত পরিমাপ এবং পরিসংখ্যানগত যাচাইকরণের মাধ্যমে প্রতিটি চলকের প্রভাব পরীক্ষা করেছেন। গবেষণাপত্রের মূল শনাক্তকারী সূত্র {f'DOI: `{doi}`' if doi else journal} অনুযায়ী সকল পদ্ধতিগত ধাপ নথিভুক্ত করা হয়েছে।

## প্রধান ফলাফল

উপাত্ত বিশ্লেষণে দেখা গেছে যে পরীক্ষিত জৈবিক উপাদানগুলোর মধ্যে সুনির্দিষ্ট কাঠামোগত ও কার্যকরী সম্পর্ক বিদ্যমান। নিয়ন্ত্রিত গ্রুপের তুলনায় পরীক্ষামূলক নমুনায় পরিমাপযোগ্য পরিবর্তন লক্ষ্য করা গেছে, যা লেখকদের প্রাথমিক বৈজ্ঞানিক অনুমানকে সমর্থন করে। তবে পর্যবেক্ষণমূলক সহসম্পর্ক এবং প্রত্যক্ষ কার্যকারণ সম্পর্কের পার্থক্য বজায় রেখেই ফলাফলগুলো ব্যাখ্যা করা হয়েছে।

## বৈজ্ঞানিক গুরুত্ব

সংশ্লিষ্ট জীববিজ্ঞান শাখায় এই ফলাফল ভবিষ্যৎ মৌলিক গবেষণা ও পদ্ধতিগত উন্নয়নে সহায়ক তথ্যভাণ্ডার হিসেবে কাজ করবে। অন্যান্য স্বাধীন গবেষণাগারে এই ফলাফল পুনরুৎপাদিত হলে বিষয়টির তাত্ত্বিক ভিত্তি আরও সুদৃঢ় হবে।

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


def create_ai_provider_from_env() -> AIProvider:
    provider_kind = os.getenv("AI_PROVIDER", "mock").strip().lower()
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    base_url = os.getenv("AI_BASE_URL", "").strip()
    temperature = float(os.getenv("AI_TEMPERATURE", "0.2"))

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
            model=model or "gemini-2.5-flash",
            temperature=temperature,
        )
    if provider_kind == "anthropic":
        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-3-5-haiku-latest",
            temperature=temperature,
        )
    raise AIProviderError(
        f"Unsupported AI_PROVIDER='{provider_kind}'. Choose mock, openai, openai_compatible, gemini, or anthropic."
    )
