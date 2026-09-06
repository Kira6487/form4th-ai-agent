import inspect
from typing import Any

from app.core.config import Settings


class CrawlerUnavailableError(RuntimeError):
    pass


class WebCrawlerProvider:
    async def start_crawl(self, url: str, max_pages: int) -> str:
        raise NotImplementedError

    async def get_crawl_status(self, external_job_id: str) -> dict[str, Any]:
        raise NotImplementedError


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {"value": value}


class FirecrawlProvider(WebCrawlerProvider):
    """Adapter around firecrawl-py; application code does not depend on its SDK types."""

    def __init__(self, settings: Settings):
        if not settings.firecrawl_api_key:
            raise CrawlerUnavailableError("Firecrawl is not configured")
        try:
            from firecrawl import AsyncFirecrawl
        except ImportError as exc:
            raise CrawlerUnavailableError("Firecrawl SDK is not installed") from exc
        self.client = AsyncFirecrawl(api_key=settings.firecrawl_api_key)

    async def _call(self, method: Any, *args: Any, **kwargs: Any) -> Any:
        result = method(*args, **kwargs)
        return await result if inspect.isawaitable(result) else result

    async def start_crawl(self, url: str, max_pages: int) -> str:
        client = getattr(self.client, "v1", self.client)
        if hasattr(client, "async_crawl_url"):
            from firecrawl.v1.client import V1ScrapeOptions
            result = await self._call(
                client.async_crawl_url,
                url,
                limit=max_pages,
                crawl_entire_domain=False,
                allow_external_links=False,
                allow_subdomains=False,
                scrape_options=V1ScrapeOptions(formats=["markdown"], onlyMainContent=True),
            )
        elif hasattr(client, "start_crawl"):
            result = await self._call(client.start_crawl, url=url, limit=max_pages, formats=["markdown"])
        elif hasattr(client, "crawl"):
            result = await self._call(client.crawl, url=url, limit=max_pages, scrape_options={"formats": ["markdown"]}, wait_until_done=False)
        else:
            raise CrawlerUnavailableError("Installed Firecrawl SDK has no asynchronous crawl method")
        payload = _as_dict(result)
        job_id = payload.get("id") or payload.get("jobId") or payload.get("job_id")
        if not job_id:
            raise CrawlerUnavailableError("Firecrawl did not return a crawl job id")
        return str(job_id)

    async def get_crawl_status(self, external_job_id: str) -> dict[str, Any]:
        client = getattr(self.client, "v1", self.client)
        method = getattr(client, "check_crawl_status", None) or getattr(client, "get_crawl_status", None)
        if method is None:
            raise CrawlerUnavailableError("Installed Firecrawl SDK has no crawl status method")
        return _as_dict(await self._call(method, external_job_id))
