import scrapy
import chompjs
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


def modify_url(url):
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}/review"


class TokopediaSpider(scrapy.Spider):
    name = 'tokopedia'
    start_urls = ['https://www.tokopedia.com/liger-official/liger-handsfree-headset-earphone-l-10-metal-stereo-bass-merah?source=homepage.top_carousel.0.39123']

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        # zyte api settings to overcome anti-scraping
        "ADDONS": {
            "scrapy_zyte_api.Addon": 500
        },
        # playwright settings to use headless browser
        "TWISTED_REACTOR": 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
    }

    def start_requests(self):  # Renamed from start to start_requests
        for url in self.start_urls:
            # modify the url and set playwright integration
            yield scrapy.Request(
                url=modify_url(url),
                dont_filter=True,
                meta={
                    # "zyte_api_automap": {"browserHtml": True},
                    "plawright": True,
                    "playwright_include_page": True,
                }
            )

    def parse(self, response):  # Make this an async method
        # get the script tag. It is the second script inside the body tag
        # script = response.css("body script::text")[1].get()
        # data = chompjs.parse_js_object(script)
        # self.logger.info(data)


        for article in response.css("section#review-feed").css("article"):
            text_star = article.css('div[class="rating"][data-testid="icnStarRating"]').attrib['aria-label']
            star = int(text_star.split(' ')[-1])
            review_box = article.css('span[data-testid="lblItemUlasan"]')

            # press "show more" button if available
            p_review_box = article.xpath('.//span[@data-testid="lblItemUlasan"]/..')
            show_more_button = p_review_box.css('button')
            if show_more_button:
                self.logger.info("Show more button found")

            review = review_box.css('::text').get()

            yield {
                "star": star,
                "review": review
            }

            # Handle pagination if needed
            # next_page = response.css('button[aria-label="Laman berikutnya"]')
            # if next_page:
            #     await page.click('button[aria-label="Laman berikutnya"]')
            #     await asyncio.sleep(2)  # Wait for page to load
            #     next_url = page.url
            #     yield scrapy.Request(url=next_url, callback=self.parse, meta={"playwright": True, "playwright_include_page": True})
