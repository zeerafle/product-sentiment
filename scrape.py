import json
from base64 import b64decode

import scrapy
import logging
from rich.logging import RichHandler
from urllib.parse import urlparse
from dotenv import load_dotenv
from scrapy.utils.log import configure_logging

# Disable Scrapy's default logging
configure_logging(install_root_handler=False)

# Configure Rich logging
FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

# Make sure all Scrapy loggers use our configuration
logger = logging.getLogger("scrapy")
logger.propagate = True

load_dotenv()


def modify_url(url):
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}/review"


class TokopediaSpider(scrapy.Spider):
    name = 'tokopedia'

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        # use Zyte API to overcome website's anti-scraping prevention
        "ADDONS": {
            "scrapy_zyte_api.Addon": 500
        }
    }

    def start_requests(self):
        yield scrapy.Request(
            url='https://www.tokopedia.com/discovery/deals',
            callback=self.parse,
            meta={
                "zyte_api_automap": {
                    "browserHtml": True,
                    "javascript": True,
                    "actions": [
                        {
                            "action": "scrollBottom",
                            "onError": "continue"
                        },
                        {
                            "action": "waitForSelector",
                            "selector": {
                                "type": "css",
                                "value": "img[alt='product-image']"
                            },
                            "timeout": 15
                        }
                    ]
                }
            }
        )

    def parse(self, response):
        for a in response.css('div.intersection-visible-wrapper div.carousel a'):
            url = a.attrib['href']
            yield response.follow(
                url=modify_url(url),
                callback=self.parse_review,
                meta={
                    "zyte_api_automap": {
                        "browserHtml": True,
                        "javascript": True,
                        "actions": [
                                       # Wait for the pagination button to be available
                                       {
                                           "action": "waitForSelector",
                                           "selector": {
                                               "type": "css",
                                               "value": 'button[aria-label="Laman berikutnya"]'
                                           }
                                       },
                                       # Click the next page button
                                       {
                                           "action": "click",
                                           "selector": {
                                               "type": "css",
                                               "value": 'button[aria-label="Laman berikutnya"]'
                                           }
                                       },
                                       {
                                           "action": "waitForResponse",
                                           "urlPattern": "/productReviewList",
                                           "urlMatchingOptions": "contains",
                                           "timeout": 15,
                                           "onError": "continue"
                                       },
                                   ] * 50,  # click the next button 50 times
                        "networkCapture": [
                            {
                                "filterType": "url",
                                "httpResponseBody": True,
                                "value": "/productReviewList",
                                "matchType": "contains",
                            }
                        ],
                    },
                }
            )

    # def start_requests(self):  # Renamed from start to start_requests
    #     for url in self.start_urls:
    #         # modify the url and set playwright integration
    #         yield scrapy.Request(
    #             url=modify_url(url),
    #             dont_filter=True,
    #             meta={
    #                 "zyte_api_automap": {
    #                     "browserHtml": True,
    #                     "javascript": True,
    #                     "actions": [
    #                                    # Wait for the pagination button to be available
    #                                    {
    #                                        "action": "waitForSelector",
    #                                        "selector": {
    #                                            "type": "css",
    #                                            "value": 'button[aria-label="Laman berikutnya"]'
    #                                        }
    #                                    },
    #                                    # Click the next page button
    #                                    {
    #                                        "action": "click",
    #                                        "selector": {
    #                                            "type": "css",
    #                                            "value": 'button[aria-label="Laman berikutnya"]'
    #                                        }
    #                                    },
    #                                    {
    #                                        "action": "waitForResponse",
    #                                        "urlPattern": "/productReviewList",
    #                                        "urlMatchingOptions": "contains",
    #                                        "timeout": 15,
    #                                        "onError": "continue"
    #                                    },
    #                                ] * 50,  # click the next button 50 times
    #                     "networkCapture": [
    #                         {
    #                             "filterType": "url",
    #                             "httpResponseBody": True,
    #                             "value": "/productReviewList",
    #                             "matchType": "contains",
    #                         }
    #                     ],
    #                 },
    #             }
    #         )

    def parse_review(self, response):
        # extract and yield data from network capture
        if 'networkCapture' in response.raw_api_response:
            self.logger.info(f"Extracting data from network capture")
            for capture in response.raw_api_response['networkCapture']:
                data = json.loads(b64decode(capture["httpResponseBody"]).decode())
                yield from self.process_review_data(data, response.url)

        # extract data from html as fallback
        self.logger.info(f"Extracting data from html")
        shop_name = response.css("div[data-testid='llbPDPFooterShopName'] h2::text").get()
        parsed_url = urlparse(response.url)
        shop_url = f"{parsed_url.scheme}://{parsed_url.netloc}/{parsed_url.path.split('/')[1]}"
        product_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        for article in response.css("section#review-feed article"):
            text_star = article.css('div[class="rating"][data-testid="icnStarRating"]').attrib['aria-label']
            star = int(text_star.split(' ')[-1])
            review = article.css('span[data-testid="lblItemUlasan"]::text').get()

            yield {
                "product_id": "",
                "product_url": product_url,
                "shop_id": "",
                "shop_name": shop_name,
                "shop_url": shop_url,
                "review_id": "",
                "star": star,
                "review": review,
                "source": "html",
                "variant_name": "",
                "is_anonymous": "",
            }

    def process_review_data(self, data, url):
        """Process review data from API response"""
        try:
            parsed_url = urlparse(url)
            product_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

            if 'data' in data[0] and 'productrevGetProductReviewList' in data[0]['data']:
                product_reviews = data[0]['data']['productrevGetProductReviewList']
                product_id = product_reviews['productID']
                shop_id = product_reviews['shop']['shopID']
                shop_name = product_reviews['shop']['name']
                shop_url = product_reviews['shop']['url']

                for review in product_reviews['list']:
                    review_id = review['id']
                    variant_name = review['variantName']
                    message = review['message']
                    rating = review['productRating']
                    is_anonymous = review['isAnonymous']

                    yield {
                        "product_id": product_id,
                        "product_url": product_url,
                        "shop_id": shop_id,
                        "shop_name": shop_name,
                        "shop_url": shop_url,
                        "review_id": review_id,
                        "star": rating,
                        "review": message,
                        "source": "api",
                        "variant_name": variant_name,
                        "is_anonymous": is_anonymous,
                    }
                    return None
                return None
            return None

        except Exception as e:
            self.logger.error(f"Error processing review data: {e}")
            self.logger.debug(f"Data structure: {data}")
            return []
