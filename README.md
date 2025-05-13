# Product Sentiment Analysis

## Installation

1. Install PDM
    ```bash
    curl -sSL https://pdm-project.org/install-pdm.py | python3 -
    ```
2. Install dependencies (sync environment)
    ```bash
    pdm sync
    ```

### (Optional) Scraping Installation

1. Sign up for Zyte API (for scraping). Modify .env.example to .env and put your API key there
    ```bash
    cp .env.example .env
    ```
2. Install browser for Playwright to use
    ```bash
    pdm run playwright install chromium
    ```
3. Run scraping
    ```bash
    pdm run scrape -o reviews.jsonl
    ```
