import asyncio
from time import monotonic

import httpx
from pydantic import BaseModel, Field, PrivateAttr


class SourcePolicy(BaseModel):
    request_per_second: int = Field(gt=0)
    max_attempts: int = Field(default=4, gt=0)
    _next_request: float = PrivateAttr(default=0)  # time until next request
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    @property
    def interval(self) -> float:
        return 1 / self.request_per_second


class HTTPClient:
    def __init__(self, sources: dict[str, SourcePolicy]):
        self.client = httpx.AsyncClient(timeout=30)
        self.sources = sources

    async def get(self, source: str, url: str):
        if self.sources.get(source) is None:
            raise ValueError(f"source {source} is not supported")
        policy: SourcePolicy = self.sources.get(source)
        if policy.max_attempts < 1:
            raise ValueError("attemps must be greater than or equal to 1")
        async with policy._lock:
            for attempt in range(policy.max_attempts):
                await asyncio.sleep(max(0, policy._next_request - monotonic()))
                policy._next_request = monotonic() + policy.interval

                try:
                    response = await self.client.get(url)
                    response.raise_for_status()
                    return response.content

                except httpx.HTTPError:
                    if attempt == policy.max_attempts - 1:
                        raise
                await asyncio.sleep(2**attempt)
        raise ValueError("url is unreachable")

    async def close(self):
        await self.client.aclose()
