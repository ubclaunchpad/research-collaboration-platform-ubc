from urllib3 import Retry
from pydantic import BaseModel, PrivateAttr, Field
import time
import asyncio
from time import monotonic
import httpx

class SourcePolicy(BaseModel):
    request_per_second: int
    interval: float = PrivateAttr(default=1/request_per_second)
    max_attempts: int = Field(default=4, gt=0)
    next_request: float = 0                                     # time until next request
    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
        
class HTTPClient:
    def __init__(self, sources: dict[str, SourcePolicy]):
        self.client = httpx.AsyncClient(timeout=30)
        self.sources = sources
    
    async def get(self, source: str, url:str):
        if self.sources.get(source) is None:
            raise ValueError(f"source {source} is not supported")
        policy: SourcePolicy = self.sources.get(source)
        if policy.max_attempts < 1:
            raise ValueError("attemps must be greater than or equal to 1")
        async with policy.lock:
            for attempt in range(policy.max_attempts):
                await asyncio.sleep(max(0, limit.next_request - monotonic()))
                policy.next_request = monotonic() + policy.interval
                
                try:
                    response = await self.client.get(url)
                    response.raise_for_status()
                    return response.content
                
                except Error as e:
                    if attempt == policy.max_attempts - 1:
                        raise 
                await asyncio.sleep(2**attempt)
        raise ValueError("url is unreachable")
        
    async def close(self):
        await self.client.aclose()
        

