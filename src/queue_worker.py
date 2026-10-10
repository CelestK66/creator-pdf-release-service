from __future__ import annotations

import asyncio
from typing import Any, Protocol


class JobClient(Protocol):
    async def get_job(self, job_id: str) -> dict[str, Any]:
        raise AssertionError("Protocol method called directly")


SUCCESS_STATES = {"completed", "succeeded"}
END_STATES = SUCCESS_STATES | {"failed", "cancelled"}


async def await_pdf_job(
    client: JobClient,
    job_id: str,
    *,
    poll_interval: float = 0.5,
    max_polls: int = 120,
) -> dict[str, Any]:
    for _ in range(max_polls):
        job = await client.get_job(job_id)
        status = job.get("status")
        if status in SUCCESS_STATES:
            return job
        if status in END_STATES:
            raise RuntimeError(f"PDF job {job_id} ended with status {status}")
        await asyncio.sleep(poll_interval)
    raise TimeoutError(f"PDF job {job_id} did not finish within the polling window")
