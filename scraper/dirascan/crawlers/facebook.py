from dirascan.base.crawler import BaseCrawler, SearchFilters, RawListing


class FacebookCrawler(BaseCrawler):
    """
    Scraper for Facebook groups listing apartments for rent.

    Implementation notes:
    - Uses the `facebook-scraper` library (pip install facebook-scraper).
    - Requires FACEBOOK_EMAIL + FACEBOOK_PASSWORD in env (set in .env).
    - Target groups are public Facebook groups, e.g.:
        https://www.facebook.com/groups/dira.lehaskir.tlv
    - Posts are free-text Hebrew; price, rooms, neighborhood, and floor
      are extracted via regex in dirascan.nlp.hebrew.
    - source_id = post ID from Facebook (e.g., "1234567890123456").
    - Anti-bot: rate-limit requests; facebook-scraper uses cookie-based auth.
    """

    source_name = "facebook"

    # Facebook group IDs / slugs to scrape — extend as needed
    GROUP_IDS: list[str] = []

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        # TODO: implement facebook-scraper based scraping + Hebrew NLP extraction
        raise NotImplementedError("FacebookCrawler.scrape() not yet implemented")
