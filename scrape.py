import json
from base64 import b64decode

import scrapy
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


def modify_url(url):
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}/review"


class TokopediaSpider(scrapy.Spider):
    name = 'tokopedia'
    start_urls = [
        'https://www.tokopedia.com/discovery/deals',
        'https://www.tokopedia.com/p/rumah-tangga',
        'https://www.tokopedia.com/p/audio-kamera-elektronik-lainnya',
        'https://www.tokopedia.com/p/buku',
        'https://www.tokopedia.com/p/dapur',
        'https://www.tokopedia.com/p/elektronik',
        'https://www.tokopedia.com/p/fashion-anak-bayi',
        'https://www.tokopedia.com/p/fashion-muslim',
        'https://www.tokopedia.com/p/fashion-wanita',
        'https://www.tokopedia.com/p/film-musik',
        'https://www.tokopedia.com/p/gaming',
        'https://www.tokopedia.com/p/handphone-tablet',
        'https://www.tokopedia.com/p/ibu-bayi',
        'https://www.tokopedia.com/p/kecantikan',
        'https://www.tokopedia.com/p/kesehatan',
        'https://www.tokopedia.com/p/komputer-laptop',
        'https://www.tokopedia.com/p/mainan-hobi',
        'https://www.tokopedia.com/p/makanan-minuman',
        'https://www.tokopedia.com/p/office-stationery',
        'https://www.tokopedia.com/p/olahraga',
        'https://www.tokopedia.com/p/otomotif',
        'https://www.tokopedia.com/p/perawatan-hewan',
        'https://www.tokopedia.com/p/perawatan-tubuh',
        'https://www.tokopedia.com/p/perlengkapan-pesta',
        'https://www.tokopedia.com/p/pertukangan'
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        # use Zyte API to overcome website's anti-scraping prevention
        "ADDONS": {
            "scrapy_zyte_api.Addon": 500
        }
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "zyte_api_automap": {
                        "browserHtml": True,
                        "javascript": True,
                        "actions": [
                            {
                                "action": "waitForSelector",
                                "selector": {
                                    "type": "css",
                                    "value": "article[aria-labelledby='unf-modal-title']"
                                },
                                "onError": "continue",
                            },
                            {
                                "action": "click",
                                "selector": {
                                    "type": "css",
                                    "value": "article[aria-labelledby='unf-modal-title'] button"
                                },
                                "onError": "continue",
                            },
                            {
                                "action": "scrollBottom",
                                "onError": "continue",
                                "scrollStep": 70
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
        all_as = response.css('div.intersection-visible-wrapper div.carousel a') + response.css(
            'div[id="divComp#67"] a')
        for a in all_as:
            url = a.attrib['href']
            yield response.follow(
                url=modify_url(url),
                callback=self.parse_review,
                meta={
                    "zyte_api_automap": {
                        "browserHtml": True,
                        "javascript": True,
                        "actions": [
                            {
                                "action": "waitForSelector",
                                "selector": {
                                    "type": "css",
                                    "value": "section#review-feed article span[data-testid='lblItemUlasan']"
                                }
                            },
                            {
                                "action": "click",
                                "selector": {
                                    "type": "xpath",
                                    "value": "//section[@id='review-feed']/article//button[text()='Selengkapnya']"
                                },
                                "onError": "continue"
                            },
                            {
                                # Wait for the pagination button to be available
                                "action": "waitForSelector",
                                "selector": {
                                    "type": "css",
                                    "value": 'button[aria-label="Laman berikutnya"]'
                                }
                            },
                            {
                                # Click the next page button
                                "action": "click",
                                "selector": {
                                    "type": "css",
                                    "value": 'button[aria-label="Laman berikutnya"]'
                                },
                                "onError": "return" # stops the action chain if the button is not found
                            },
                            {
                                "action": "waitForResponse",
                                "urlPattern": "/productReviewList",
                                "urlMatchingOptions": "contains",
                                "timeout": 15,
                                "onError": "continue"
                            },
                        ] * 99,  # click the next button as many times as possible
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
        product_url = f"{parsed_url.scheme}://{parsed_url.netloc}{'/'.join(parsed_url.path.split('/')[:-1])}"

        for article in response.css("section#review-feed article"):
            text_star = article.css('div[class="rating"][data-testid="icnStarRating"]').attrib['aria-label']
            star = int(text_star.split(' ')[-1])
            review = article.css('span[data-testid="lblItemUlasan"]::text').get()

            yield {
                "product_id": None,
                "product_url": product_url,
                "shop_id": None,
                "shop_name": shop_name,
                "shop_url": shop_url,
                "review_id": None,
                "star": star,
                "review": review,
                "source": "html",
                "variant_name": None,
                "is_anonymous": None,
            }

    def process_review_data(self, data, url):
        """Process review data from API response"""
        try:
            parsed_url = urlparse(url)
            product_url = f"{parsed_url.scheme}://{parsed_url.netloc}{'/'.join(parsed_url.path.split('/')[:-1])}"

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
