from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .creator_release import CreatorDelivery, CreatorDeliveryRequest, build_creator_delivery
from .infrai_pdf import InfraiError, InfraiPdfClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    app.state.pdf_client = InfraiPdfClient(api_key)
    yield
    await app.state.pdf_client.close()


app = FastAPI(title="Creator PDF Delivery", lifespan=lifespan)


@app.exception_handler(InfraiError)
async def handle_infrai_error(_: Request, exc: InfraiError) -> JSONResponse:
    status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": exc.code, "message": str(exc)}},
    )


@app.post("/creator-deliveries", response_model=CreatorDelivery)
async def create_creator_delivery(
    body: CreatorDeliveryRequest,
    request: Request,
) -> CreatorDelivery:
    return await build_creator_delivery(body, request.app.state.pdf_client)
