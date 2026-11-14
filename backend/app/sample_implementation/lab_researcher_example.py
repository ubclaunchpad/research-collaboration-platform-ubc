import asyncio

from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.adapter_interface import adapter
from app.http_client import HTTPClient, SourcePolicy


class Lab_Researcher(BaseModel):
    name: str
    title: str
    email: str | None = None


class lab_leader_crawler(adapter):
    def __init__(self, client: HTTPClient, url: str):
        self.client = client
        self.url = url

    async def fetch(self):
        return await self.client.get("lab_policy", self.url)

    def normalize(self, response) -> Lab_Researcher:
        soup = BeautifulSoup(response, "html.parser")

        hero = soup.select_one(".hero-section")
        if hero is None:
            raise ValueError("Hero section not found")
        name_tag = hero.select_one(".title-container h1")
        title_tag = hero.select_one(".title-container h4")

        name = name_tag.get_text(strip=True)
        title = title_tag.get_text(strip=True)

        email_tag = hero.select_one('a[href^="mailto:"]')
        if email_tag:
            email = email_tag["href"].removeprefix("mailto:")
        else:
            email = None

        return Lab_Researcher(name=name, title=title, email=email)


async def main():
    client = HTTPClient({"lab_policy": SourcePolicy(request_per_second=1)})

    try:
        crawler = lab_leader_crawler(
            client,
            "https://lsi.ubc.ca/people/ninan-abraham/",
        )
        html = await crawler.fetch()
        result = crawler.normalize(html)
        print(result.name, result.title, result.email)
        crawler.store(result.model_dump(), "Prof_Pages")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
