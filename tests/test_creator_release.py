from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from src.creator_release import AssetIngestion, CreatorDeliveryRequest, build_creator_delivery
from src.infrai_pdf import InfraiPdfClient


class RecordingPdfClient:
    def __init__(self) -> None:
        self.call: dict[str, Any] = {}

    async def generate_release(self, **kwargs: Any) -> dict[str, Any]:
        self.call = kwargs
        return {"pdf": "https://cdn.example.test/releases/release-42.pdf"}


def test_creator_release_renders_template_and_uses_delivery_id_for_retry_safety() -> None:
    client = RecordingPdfClient()
    request = CreatorDeliveryRequest(
        delivery_id="release-42",
        creator_id="creator-7",
        asset=AssetIngestion(
            asset_id="brief-template",
            template_html="<h1>{{creator_name}}</h1><p>{{campaign_title}}</p>",
        ),
        template_vars={"creator_name": "Mina", "campaign_title": "Studio Notes"},
    )

    delivery = asyncio.run(build_creator_delivery(request, client))

    assert client.call == {
        "template_html": "<h1>{{creator_name}}</h1><p>{{campaign_title}}</p>",
        "template_vars": {"creator_name": "Mina", "campaign_title": "Studio Notes"},
        "store": True,
        "idempotency_key": "release-42",
    }
    assert delivery.state == "ready"
    assert delivery.asset_id == "brief-template"


def test_generate_release_sends_idempotency_key_in_request_body() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["idempotency_key"] == "release-42"
        assert "Idempotency-Key" not in request.headers
        return httpx.Response(200, json={"ok": True, "data": {"pdf": "result"}})

    async def exercise() -> None:
        client = InfraiPdfClient("test-key", transport=httpx.MockTransport(handler))
        try:
            await client.generate_release(
                template_html="<h1>{{creator_name}}</h1>",
                template_vars={"creator_name": "Mina"},
                store=True,
                idempotency_key="release-42",
            )
        finally:
            await client.close()

    asyncio.run(exercise())
