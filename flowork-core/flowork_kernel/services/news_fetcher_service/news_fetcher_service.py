#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\news_fetcher_service\news_fetcher_service.py JUMLAH BARIS 121 
#######################################################################

import requests
import xml.etree.ElementTree as ET
from ..base_service import BaseService
import time
from threading import Lock, Thread
import re
class NewsFetcherService(BaseService):
    NEWS_URL = (
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCULzlhJUh-_VjdCXu-GouOQ"
    )
    CACHE_DURATION_SECONDS = 900  # Cache for 15 minutes
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self._cache = None
        self._last_fetch_time = 0
        self._lock = Lock()
        self.logger("Service 'NewsFetcherService' initialized.", "DEBUG")  # English Log
        self.start_background_fetch()
    def start_background_fetch(self):
        thread = Thread(target=self.get_news, daemon=True)
        thread.start()
    def get_news(self):
        """
        Fetches news from the RSS/Atom feed, using a time-based cache.
        Returns a list of news articles as dictionaries.
        """
        with self._lock:
            if self._cache and (
                time.time() - self._last_fetch_time < self.CACHE_DURATION_SECONDS
            ):
                self.logger("Returning news from cache.", "DEBUG")  # English Log
                return self._cache
            self.logger(
                "Fetching fresh news from YouTube RSS feed...", "INFO"
            )  # English Log
            try:
                response = requests.get(self.NEWS_URL, timeout=15)
                response.raise_for_status()
                root = ET.fromstring(response.content)
                atom_namespace = "{http://www.w3.org/2005/Atom}"
                media_namespace = (
                    "{http://search.yahoo.com/mrss/}"  # Untuk thumbnail dan deskripsi
                )
                self.logger(
                    f"Detected XML namespace: '{atom_namespace}'", "DEBUG"
                )  # English Log
                news_list = []
                entries = root.findall(f"{atom_namespace}entry")
                if not entries:
                    self.logger(
                        f"Could not find <entry> tags in the YouTube feed. Root tag is '{root.tag}'.",
                        "ERROR",
                    )  # English Log
                    return {"error": "Could not parse YouTube feed (no entries found)."}
                for item in entries:
                    title_tag = item.find(f"{atom_namespace}title")
                    link_tag = item.find(f"{atom_namespace}link[@rel='alternate']")
                    published_tag = item.find(f"{atom_namespace}published")
                    media_thumbnail_tag = item.find(
                        f"{media_namespace}group/{media_namespace}thumbnail"
                    )
                    media_description_tag = item.find(
                        f"{media_namespace}group/{media_namespace}description"
                    )
                    snippet = "No description available."
                    image_url = None
                    if media_description_tag is not None and media_description_tag.text:
                        plain_text = media_description_tag.text.strip()
                        snippet = (
                            (plain_text[:200] + "...")
                            if len(plain_text) > 200
                            else plain_text
                        )
                    if media_thumbnail_tag is not None:
                        image_url = media_thumbnail_tag.get("url")
                    article = {
                        "title": (
                            title_tag.text if title_tag is not None else "No Title"
                        ),
                        "link": (
                            link_tag.get("href") if link_tag is not None else "#"
                        ),  # Pastikan mengambil 'href'
                        "pubDate": (
                            published_tag.text
                            if published_tag is not None
                            else "No Date"
                        ),
                        "description": snippet,
                        "imageUrl": image_url,
                    }
                    news_list.append(article)
                self._cache = news_list
                self._last_fetch_time = time.time()
                self.logger(
                    f"Successfully fetched and parsed {len(news_list)} YouTube articles.",
                    "SUCCESS",
                )  # English Log
                return news_list
            except requests.exceptions.RequestException as e:
                self.logger(
                    f"Failed to fetch YouTube RSS feed: {e}", "ERROR"
                )  # English Log
                return {"error": "Could not connect to the YouTube news source."}
            except ET.ParseError as e:
                self.logger(
                    f"Failed to parse XML from YouTube RSS feed: {e}", "ERROR"
                )  # English Log
                return {"error": "The YouTube news source format is invalid."}
            except Exception as e:
                self.logger(
                    f"An unexpected error occurred in NewsFetcherService: {e}",
                    "CRITICAL",
                )  # English Log
                return {"error": "An unexpected error occurred."}
