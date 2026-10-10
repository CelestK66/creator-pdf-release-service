from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .queue_worker import await_pdf_job


class PdfClient(Protocol):
    async def generate_release(
        self,
        *,
        template_html: str,
        template_vars: dict[str, str],
        store: bool,
        idempotency_key: str,
    ) -> dict[str, Any]:
        raise AssertionError("Protocol method called directly")

    async def get_job(self, job_id: str) -> dict[str, Any]:
        raise AssertionError("Protocol method called directly")


class AssetIngestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)
    template_html: str = Field(min_length=1, description="HTML for the creator release")


class CreatorDeliveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    asset: AssetIngestion
    template_vars: dict[str, str] = Field(min_length=1)


class CreatorDelivery(BaseModel):
    delivery_id: str
    creator_id: str
    asset_id: str
    state: str
    result: dict[str, Any]


async def build_creator_delivery(
    request: CreatorDeliveryRequest,
    client: PdfClient,
) -> CreatorDelivery:
    result = await client.generate_release(
        template_html=request.asset.template_html,
        template_vars=request.template_vars,
        store=True,
        idempotency_key=request.delivery_id,
    )
    job_id = result.get("job_id")
    if isinstance(job_id, str) and job_id:
        result = await await_pdf_job(client, job_id)

    return CreatorDelivery(
        delivery_id=request.delivery_id,
        creator_id=request.creator_id,
        asset_id=request.asset.asset_id,
        state="ready",
        result=result,
    )
