# Product Sentiment Analysis

Sentiment analysis with classical text embedding for Tokopedia's product's reviews.

## Installation

### With PDM (recommended)

1. Install PDM
    ```bash
    curl -sSL https://pdm-project.org/install-pdm.py | python3 -
    ```
2. Install dependencies (sync environment)
    ```bash
    pdm sync
    ```

### With builtin virtual environment

1. Create virtual environment
    ```bash
    python -m venv .venv
    ```
2. Activate the virtual environment
    ```bash
    # .\.venv\Scripts\activate # windows
    ./.venv/bin/activate # linux
    ```
3. Install dependencies
    ```bash
    pip install -r requirements.txt
    ```

### (Optional) Scraping Configuration

1. Sign up for Zyte API (for scraping). Modify .env.example to .env and put your API key there. Also follow the [guide in Zyte docs](https://docs.zyte.com/misc/ca.html#ca) to install certificate.
    ```bash
    cp .env.example .env
    ```
2. Run scraping
    ```bash
    pdm run scrape -o reviews.jsonl
    ```
