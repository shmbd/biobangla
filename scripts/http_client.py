from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from typing import Any

logger = logging.getLogger("biobangla.http")

TRANSIENT_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}


class AccessRestrictedError(RuntimeError):
    """Raised when robots.txt or an HTTP 401/403 paywall/access restriction forbids fetching."""


class PoliteHttpClient:
    """
    Polite HTTP client for official open-science APIs and feeds.
    Enforces:
      - Explicit User-Agent with contact email
      - Per-host rate limiting
      - Optional robots.txt verification (never bypasses restrictions)
      - Retries with exponential backoff on transient network / 5xx / 429 errors
      - Immediate stop on 401/403 paywall or permission blocks
    """

    def __init__(
        self,
        user_agent: str,
        contact_email: str = "",
        timeout_seconds: int = 25,
        max_retries: int = 3,
        backoff_base_seconds: float = 2.0,
        respect_robots_txt: bool = True,
        sleep_fn: Any = time.sleep,
    ) -> None:
        if contact_email and contact_email not in user_agent:
            self.user_agent = f"{user_agent} (mailto:{contact_email})"
        else:
            self.user_agent = user_agent
        self.contact_email = contact_email
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.respect_robots_txt = respect_robots_txt
        self._sleep = sleep_fn
        self._last_request_by_host: dict[str, float] = {}
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _enforce_rate_limit(self, host: str, rate_limit_per_second: float) -> None:
        if rate_limit_per_second <= 0:
            return
        min_interval = 1.0 / rate_limit_per_second
        now = time.monotonic()
        last = self._last_request_by_host.get(host)
        if last is not None:
            elapsed = now - last
            if elapsed < min_interval:
                self._sleep(min_interval - elapsed)
        self._last_request_by_host[host] = time.monotonic()

    def _check_robots(self, url: str) -> None:
        if not self.respect_robots_txt:
            return
        parsed = urllib.parse.urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots_cache:
            robots_url = f"{origin}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            try:
                req = urllib.request.Request(
                    robots_url, headers={"User-Agent": self.user_agent}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        lines = resp.read().decode("utf-8", errors="replace").splitlines()
                        rp.parse(lines)
                        self._robots_cache[origin] = rp
                    else:
                        self._robots_cache[origin] = None
            except Exception:
                # If robots.txt does not exist or fails on an API subdomain, record None
                self._robots_cache[origin] = None

        parser = self._robots_cache.get(origin)
        if parser is not None and not parser.can_fetch(self.user_agent, url):
            raise AccessRestrictedError(
                f"Blocked by robots.txt policy for URL: {url}"
            )

    def get_text(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        rate_limit_per_second: float = 1.0,
        check_robots: bool = False,
    ) -> str:
        full_url = url
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
            query_string = urllib.parse.urlencode(clean_params, doseq=True)
            sep = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{sep}{query_string}"

        parsed = urllib.parse.urlparse(full_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Unsupported URL scheme: {full_url}")

        if check_robots:
            self._check_robots(full_url)

        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, application/xml, text/xml, */*;q=0.8",
        }
        if headers:
            req_headers.update(headers)

        attempt = 0
        while True:
            self._enforce_rate_limit(parsed.netloc, rate_limit_per_second)
            request = urllib.request.Request(full_url, headers=req_headers, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    return resp.read().decode(charset, errors="replace")
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 402, 403, 451):
                    # Strictly refuse to retry or bypass paywalls / permission blocks
                    raise AccessRestrictedError(
                        f"HTTP {exc.code} access restricted at {full_url}"
                    ) from exc

                if exc.code in TRANSIENT_HTTP_STATUSES and attempt < self.max_retries:
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    delay = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else self.backoff_base_seconds * (2**attempt)
                    )
                    logger.warning(
                        "Transient HTTP %s for %s; retrying in %.1fs (attempt %d/%d)",
                        exc.code,
                        full_url,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    self._sleep(delay)
                    attempt += 1
                    continue
                raise
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_base_seconds * (2**attempt)
                    logger.warning(
                        "Network error (%s) for %s; retrying in %.1fs (attempt %d/%d)",
                        exc,
                        full_url,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    self._sleep(delay)
                    attempt += 1
                    continue
                raise

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        rate_limit_per_second: float = 1.0,
    ) -> dict[str, Any]:
        merged_headers = {"Accept": "application/json"}
        if headers:
            merged_headers.update(headers)
        raw = self.get_text(
            url=url,
            params=params,
            headers=merged_headers,
            rate_limit_per_second=rate_limit_per_second,
            check_robots=False,
        )
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object from {url}")
        return data
