"""联网搜索。支持博查（国内）和 Tavily（海外），也可以不接搜索。"""

from __future__ import annotations

from typing import Protocol

import requests

from .models import SearchResult


class SearchError(RuntimeError):
    pass


SIGNUP = {"DeepSeek": "platform.deepseek.com", "博查": "open.bochaai.com", "Tavily": "tavily.com"}


def _explain(provider: str, e: Exception) -> SearchError:
    """把技术报错翻译成人话。"""
    code = getattr(getattr(e, "response", None), "status_code", None)
    site = SIGNUP.get(provider, "")
    if code in (401, 403) and provider == "DeepSeek":
        msg = "DeepSeek 不认这个 Key，检查一下 API Key 有没有复制完整。"
    elif code in (401, 403):
        msg = (f"{provider}的搜索 Key 不对，被拒绝了。注意：{provider}的 Key 和 DeepSeek 的 Key 是两个不同的东西，"
               f"要到 {site} 单独注册申请。最省事的办法是搜索也改用 DeepSeek。")
    elif code == 402 and provider == "DeepSeek":
        msg = "DeepSeek 账户余额不足，到 platform.deepseek.com 充值后再试。"
    elif code == 402 or code == 429:
        msg = f"{provider}账户的额度用完了，或者搜得太频繁。去 {site} 看看余额，或者过一会儿再试。"
    elif code is not None:
        msg = f"{provider}搜索出错了（错误码 {code}），稍后再试。"
    else:
        msg = f"连不上{provider}，检查一下网络。"
    return SearchError(msg)


class Searcher(Protocol):
    name: str

    def search(self, query: str, n: int = 5) -> list[SearchResult]: ...


class DeepSeekSearch:
    """DeepSeek 官方搜索接口，和对话用同一个 Key：https://api-docs.deepseek.com/guides/search/"""

    name = "DeepSeek"
    URL = "https://api.deepseek.com/v1/tools/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, n: int = 5) -> list[SearchResult]:
        try:
            r = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"query": query.strip()[:128], "count": n},  # 接口限制 query 最长 128 字
                timeout=30,
            )
            r.raise_for_status()
            items = r.json().get("results", []) or []
        except Exception as e:
            raise _explain("DeepSeek", e) from e
        return [
            SearchResult(
                title=i.get("title") or i.get("site_name") or "",
                url=i.get("url", ""),
                snippet=(i.get("summary") or i.get("snippet") or "")[:600],
                query=query,
            )
            for i in items
            if i.get("url")
        ]


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
            raise _explain("博查", e) from e
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
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"api_key": self.api_key, "query": query, "max_results": n},
                timeout=30,
            )
            r.raise_for_status()
            items = r.json().get("results", []) or []
        except Exception as e:
            raise _explain("Tavily", e) from e
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
