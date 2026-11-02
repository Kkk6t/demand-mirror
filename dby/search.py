"""联网搜索。支持博查（国内）和 Tavily（海外），也可以不接搜索。"""

from __future__ import annotations

from typing import Protocol

import requests

from .models import SearchResult


class SearchError(RuntimeError):
    pass


class Searcher(Protocol):
    name: str

    def search(self, query: str, n: int = 5) -> list[SearchResult]: ...


class BochaSearch:
    """博查 Web Search API：https://open.bochaai.com"""

    name = "博查"
    URL = "https://api.bochaai.com/v1/web-search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, n: int = 5) -> list[SearchResult]:
        try:
            r = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"query": query, "summary": True, "count": n},
                timeout=30,
            )
            r.raise_for_status()
            items = (r.json().get("data") or {}).get("webPages", {}).get("value", []) or []
        except Exception as e:
            raise SearchError(f"博查搜索失败：{e}") from e
        return [
            SearchResult(
                title=i.get("name", ""),
                url=i.get("url", ""),
                snippet=(i.get("summary") or i.get("snippet") or "")[:600],
                query=query,
            )
            for i in items
            if i.get("url")
        ]


class TavilySearch:
    """Tavily Search API：https://tavily.com"""

    name = "Tavily"
    URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, n: int = 5) -> list[SearchResult]:
        try:
            r = requests.post(
                self.URL,
                json={"api_key": self.api_key, "query": query, "max_results": n},
                timeout=30,
            )
            r.raise_for_status()
            items = r.json().get("results", []) or []
        except Exception as e:
            raise SearchError(f"Tavily 搜索失败：{e}") from e
        return [
            SearchResult(
                title=i.get("title", ""),
                url=i.get("url", ""),
                snippet=(i.get("content") or "")[:600],
                query=query,
            )
            for i in items
            if i.get("url")
        ]


class NoSearch:
    name = "未接入搜索"

    def search(self, query: str, n: int = 5) -> list[SearchResult]:
        return []


class DemoSearch:
    name = "演示数据"

    def __init__(self, results: dict[str, list[dict]]):
        self.results = results

    def search(self, query: str, n: int = 5) -> list[SearchResult]:
        return [SearchResult(**r, query=query) for r in self.results.get(query, [])][:n]
