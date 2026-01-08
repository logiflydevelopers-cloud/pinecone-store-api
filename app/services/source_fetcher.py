# app/repos/source_fetcher.py

import requests
from typing import Tuple

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# 25 MB safety limit
MAX_DOWNLOAD_SIZE = 25 * 1024 * 1024


def fetch_source(source: str) -> Tuple[bytes, str]:
    """
    Fetch raw content from a URL.

    Returns:
    - content bytes
    - content_type (lowercased from HTTP headers)
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string URL")

    try:
        with requests.get(
            source,
            timeout=30,
            allow_redirects=True,
            headers=HEADERS,
            stream=True,
        ) as resp:

            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "").lower()

            content = bytearray()
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    content.extend(chunk)

                if len(content) > MAX_DOWNLOAD_SIZE:
                    raise ValueError("Downloaded file exceeds size limit (25MB)")

            return bytes(content), content_type

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch source: {e}")
