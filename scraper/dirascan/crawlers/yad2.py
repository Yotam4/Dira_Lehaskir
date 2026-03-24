from dirascan.base.crawler import BaseCrawler, SearchFilters, RawListing


class Yad2Crawler(BaseCrawler):
    """
    Scraper for yad2.co.il — Israel's largest real-estate classifieds.

    Implementation notes:
    - Yad2 is a JS-heavy SPA; requires Playwright (not plain requests).
    - Entry point: https://www.yad2.co.il/realestate/rent
    - Filters are encoded as URL query params: city=<code>, rooms=<min>-<max>,
      price=<min>-<max>, neighborhood=<id>
    - City codes are numeric (e.g., Tel Aviv = 5000).
    - Anti-bot: randomise viewport, user-agent rotation, request delays.
    - Listings are rendered in a virtual scroll list; scroll to paginate.
    """

    source_name = "yad2"

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        # TODO: implement Playwright-based scraping
        raise NotImplementedError("Yad2Crawler.scrape() not yet implemented")
