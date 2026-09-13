import os
import re
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger("severus.search_service")

class WebSearchService:
    """
    Web Search service providing query classification and multi-engine real-time retrieval.
    Prefers free zero-config DuckDuckGo search, with optional support for Tavily API key if set.
    """

    SEARCH_KEYWORDS = [
        "latest", "recent", "current", "news", "today", "2025", "2026",
        "release", "update", "newest", "version", "who is the current",
        "what is the current", "search web", "search online", "search the web",
        "real-time", "realtime", "trending"
    ]

    def should_search(self, query: str) -> bool:
        """
        Classifies whether a user prompt requests real-time, current, or latest information.
        Returns False for standard static Data Science and coding questions.
        """
        if not query or not isinstance(query, str):
            return False

        query_lower = query.lower()

        # Check for explicit search keywords or year markers
        for keyword in self.SEARCH_KEYWORDS:
            if keyword in query_lower:
                return True

        # Check if query explicitly asks for dates or recent events
        if re.search(r'\b(in 202[5-9]|this week|this month|now)\b', query_lower):
            return True

        return False

    def search(self, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        """
        Performs web search retrieval and returns structured results: title, snippet, url.
        Catches all network and API exceptions gracefully.
        """
        if not query:
            return []

        # 1. Optional Tavily API Search if key is provided in environment
        tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
        if tavily_key and tavily_key != "your_tavily_api_key_optional":
            try:
                res = requests.post(
                    "https://api.tavily.com/search",
                    json={"api_key": tavily_key, "query": query, "max_results": max_results},
                    timeout=5
                )
                if res.status_code == 200:
                    data = res.json()
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", "Web Result"),
                            "snippet": item.get("content", ""),
                            "url": item.get("url", "")
                        })
                    if results:
                        return results
            except Exception as e:
                logger.warning(f"Tavily search failed: {e}. Falling back to DuckDuckGo.")

        # 2. Default Zero-Config DuckDuckGo Search
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
                results = []
                for item in raw_results:
                    results.append({
                        "title": item.get("title", "Web Result"),
                        "snippet": item.get("body", ""),
                        "url": item.get("href", "")
                    })
                return results
        except Exception as e:
            logger.warning(f"DuckDuckGo search encountered an error: {e}")

        return []

search_service = WebSearchService()
