from urllib.parse import urlparse
import requests


# Domains that MUST NOT be scraped
BLOCKED_DOMAINS = [
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "accounts.google.com"
]


# Keywords indicating private or restricted pages
BLOCKED_KEYWORDS = [
    "login",
    "signin",
    "signup",
    "auth",
    "account"
]


def is_public_url(url: str) -> bool:
    """
    Validate that the URL is public and safe to fetch.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Block known private platforms
        for blocked in BLOCKED_DOMAINS:
            if blocked in domain:
                return False

        # Block login / auth pages
        for keyword in BLOCKED_KEYWORDS:
            if keyword in parsed.path.lower():
                return False

        # HEAD request to check accessibility
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code >= 400:
            return False

        return True

    except Exception:
        return False
