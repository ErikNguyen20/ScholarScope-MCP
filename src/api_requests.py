import httpx
from collections.abc import Mapping, Sequence
from typing import Any, Optional, Tuple, Union
from tenacity import Retrying, AsyncRetrying, stop_after_attempt, wait_exponential, wait_random
from tenacity import retry_if_exception_type
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import validators


ParamType = Union[Mapping[str, Any], Sequence[Tuple[str, Any]]]
RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}


class RequestAPI:
    class _RetryableStatus(Exception):
        def __init__(self, status: int, retry_after: Optional[float] = None):
            self.status = status
            self.retry_after = retry_after
            super().__init__(f"Retryable HTTP status: {status}")

    def __init__(
        self,
        base_url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        default_params: Optional[Mapping[str, Any]] = None,
        timeout: Union[float, httpx.Timeout] = 10.0,
        return_none_on_404: bool = False,
        max_retries: int = 3,
        jitter_max_seconds: float = 0.25,
    ):
        self.base_url = base_url
        self.headers = dict(headers or {})
        self.default_params = dict(default_params or {})
        self.timeout = timeout
        self.return_none_on_404 = return_none_on_404
        self.max_retries = max_retries
        self.jitter_max_seconds = jitter_max_seconds
        self._client: Optional[httpx.Client] = None
        self._aclient: Optional[httpx.AsyncClient] = None

    # ---------- Context ----------
    def __enter__(self) -> "RequestAPI":
        self._ensure_client()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    async def __aenter__(self) -> "RequestAPI":
        await self._ensure_aclient()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    # ---------- Sync ----------
    def get(self, path: str, *, params: Optional[ParamType] = None, headers: Optional[Mapping[str, str]] = None) -> Any:
        self._ensure_client()
        return self._retrying()(self._get_once, path, params, headers)

    def _get_once(self, path: str, params: Optional[ParamType], headers: Optional[Mapping[str, str]]) -> Any:
        resp = self._client.get(
            path,
            headers={**self.headers, **(headers or {})},
            params=self._merge_params(params),
            timeout=self.timeout,
        )
        self._maybe_raise_for_retry(resp)
        if resp.status_code == 404 and self.return_none_on_404:
            return None
        resp.raise_for_status()
        return self._parse(resp)

    # ---------- Async ----------
    async def aget(self, path: str, *, params: Optional[ParamType] = None, headers: Optional[Mapping[str, str]] = None) -> Any:
        await self._ensure_aclient()
        return await self._aretrying()(self._aget_once, path, params, headers)

    async def _aget_once(self, path: str, params: Optional[ParamType], headers: Optional[Mapping[str, str]]) -> Any:
        resp = await self._aclient.get(
            path,
            headers={**self.headers, **(headers or {})},
            params=self._merge_params(params),
            timeout=self.timeout,
        )
        self._maybe_raise_for_retry(resp)
        if resp.status_code == 404 and self.return_none_on_404:
            return None
        resp.raise_for_status()
        return self._parse(resp)

    # ---------- Retry builders ----------
    def _retrying(self):
        return Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.5, max=8) + wait_random(0, self.jitter_max_seconds),
            reraise=True,
            retry=retry_if_exception_type((self._RetryableStatus, httpx.RequestError)),
            before_sleep=self._maybe_sleep_until_retry_after,
        )

    def _aretrying(self):
        return AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.5, max=8) + wait_random(0, self.jitter_max_seconds),
            reraise=True,
            retry=retry_if_exception_type((self._RetryableStatus, httpx.RequestError)),
            before_sleep=self._maybe_sleep_until_retry_after,
        )

    # Tenacity hook; both sync/async receive a "retry_state"
    def _maybe_sleep_until_retry_after(self, retry_state):
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exc, self._RetryableStatus) and exc.retry_after is not None:
            retry_state.next_action.sleep = max(0.0, exc.retry_after)

    # ---------- Helpers ----------
    def _ensure_client(self):
        if self._client is None:
            self._client = httpx.Client(base_url=self.base_url)

    async def _ensure_aclient(self):
        if self._aclient is None:
            self._aclient = httpx.AsyncClient(base_url=self.base_url)

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    async def aclose(self):
        if self._aclient:
            await self._aclient.aclose()
            self._aclient = None

    def _merge_params(self, params: Optional[ParamType]) -> Any:
        if params is None:
            return {k: v for k, v in self.default_params.items() if v is not None}

        # Mapping: merge with defaults
        if isinstance(params, Mapping):
            merged = {**self.default_params, **params}
            return {k: v for k, v in merged.items() if v is not None}

        # Sequence of (key, value) pairs: pass through (let httpx handle)
        if isinstance(params, Sequence) and all(
            isinstance(p, Sequence) and len(p) == 2 for p in params  # type: ignore[arg-type]
        ):
            return params

        # Fallback: just return as-is (httpx will raise if invalid)
        return params

    def _maybe_raise_for_retry(self, resp: httpx.Response) -> None:
        if resp.status_code in RETRYABLE_STATUSES:
            retry_after = self._parse_retry_after(resp)
            raise self._RetryableStatus(resp.status_code, retry_after)

    @staticmethod
    def _parse_retry_after(resp: httpx.Response) -> Optional[float]:
        ra = resp.headers.get("Retry-After")
        if not ra:
            return None
        # HTTP allows seconds or HTTP-date
        try:
            return float(ra)
        except ValueError:
            try:
                dt = parsedate_to_datetime(ra)
            except Exception:
                return None
            if dt is None:
                return None

            # Normalize to UTC and compute positive delta
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return max(0.0, (dt - now).total_seconds())

    @staticmethod
    def _parse(resp: httpx.Response) -> Any:
        if resp.status_code == 204:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text


def validate_url_with_ssrf_guard(url: str) -> bool:
    """
    Validates a URL and rejects private/local addresses to help prevent SSRF.

    Returns:
        bool: True if the URL is valid and safe, False otherwise.
    """
    try:
        result = validators.url(
            url,
            skip_ipv6_addr=False,   # Allow IPv6 unless you have reasons to block
            skip_ipv4_addr=False,   # Allow IPv4
            may_have_port=True,     # Allow specifying ports
            simple_host=False,      # Allow complex hostnames
            strict_query=True,      # Fail if query parsing errors
            consider_tld=True,      # Restrict to valid IANA TLDs
            private=False,          # Reject private/local IPs (SSRF mitigation)
            rfc_1034=False,         # Don't allow trailing dots in hostnames
            rfc_2782=False,         # Don't treat as SRV records
            validate_scheme=lambda s: s in {"http", "https"}  # Only HTTP/HTTPS
        )
    except validators.ValidationError as e:
        return False
    return result


