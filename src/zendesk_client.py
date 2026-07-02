import requests

# Base URL  
DEFAULT_BASE_URL = "https://support.optisigns.com"

# Public endpoint
ARTICLES_ENDPOINT = "/api/v2/help_center/en-us/articles.json"


def fetch_articles(base_url: str = DEFAULT_BASE_URL, per_page: int = 30):
    """
    Fetch the first page of published Help Center articles.

    Args:
        base_url: Zendesk Help Center base URL.
        per_page: Number of articles to retrieve (default: 30).

    Returns:
        A list of raw article dictionaries returned by the Zendesk API.
    """

    # Build the full API endpoint URL
    url = f"{base_url}{ARTICLES_ENDPOINT}"

    # Request the first page with the desired number of articles
    params = {
        "page": 1,
        "per_page": per_page,
    }

    # Send the HTTP GET request
    resp = requests.get(url, params=params, timeout=30)

    # Raise an exception if the request failed (4xx/5xx)
    resp.raise_for_status()

    # Parse the JSON response
    payload = resp.json()

    # Return only the articles list
    return payload.get("articles", [])


if __name__ == "__main__":
    articles = fetch_articles()

    print(f"Fetched {len(articles)} articles.")