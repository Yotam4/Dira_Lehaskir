from dirascan.base.crawler import BaseCrawler, SearchFilters, RawListing


class MadlanCrawler(BaseCrawler):
    """
    Scraper for madlan.co.il — real-estate portal with map-centric search.

    Implementation notes:
    - Madlan loads listings via a GraphQL API; can be called directly with
      the right headers rather than rendering the full SPA.
    - Entry point: https://www.madlan.co.il/for-rent/<city-slug>
    - Supports bounding-box queries via GraphQL variables.
    - Anti-bot: include referer + cookie headers captured from a real browser
      session; rotate user-agents.
    """

    source_name = "madlan"

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        # TODO: implement Madlan GraphQL / Playwright scraping
        raise NotImplementedError("MadlanCrawler.scrape() not yet implemented")
