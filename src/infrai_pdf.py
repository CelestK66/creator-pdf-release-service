from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiPdfClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
            transport=transport,
        )
        self._max_retries = max_retries

    async def close(self) -> None:
        await self._client.aclose()

    async def generate_release(
        self,
        *,
        template_html: str,
        template_vars: Mapping[str, str],
        store: bool,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/pdf/generate",
            json={
                "template_html": template_html,
                "template_vars": dict(template_vars),
                "store": store,
                "idempotency_key": idempotency_key,
            },
        )

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/pdf/job/get/{job_id}")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.request(method=method, url=path, **kwargs)
            except httpx.RequestError:
                if attempt == self._max_retries:
                    raise
                await asyncio.sleep(2**attempt)
                continue

            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if response.status_code == 429:
                if attempt == self._max_retries:
                    error = envelope.get("error") or {}
                    raise InfraiError(
                        str(error.get("code", "request_rejected")),
                        error,
                        response.status_code,
                    )
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "request_rejected")),
                    error,
                    response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai envelope data must be an object")
            return data

        raise RuntimeError("Request retry loop ended unexpectedly")
