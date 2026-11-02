"""根据配置组装模型和搜索。没有 API Key 时自动进入演示模式。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .demo import DEMO_RESPONSES, DEMO_SEARCH
from .llm import LLM, DemoLLM, OpenAICompatLLM
from .search import BochaSearch, NoSearch, Searcher, TavilySearch, DemoSearch

PRESETS = {
    "DeepSeek": ("https://api.deepseek.com", "deepseek-chat"),
    "通义千问": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    "Kimi": ("https://api.moonshot.cn/v1", "moonshot-v1-32k"),
    "OpenAI": ("https://api.openai.com/v1", "gpt-4o-mini"),
}


@dataclass
class Settings:
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    search_provider: str = "博查"  # 博查 / Tavily / 不接搜索
    search_api_key: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        base, model = PRESETS["DeepSeek"]
        return cls(
            llm_base_url=os.getenv("LLM_BASE_URL", base),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", model),
            search_provider=os.getenv("SEARCH_PROVIDER", "博查"),
            search_api_key=os.getenv("SEARCH_API_KEY", ""),
        )

    @property
    def demo(self) -> bool:
        return not self.llm_api_key.strip()


def build_demo() -> tuple[LLM, Searcher]:
    return DemoLLM(DEMO_RESPONSES), DemoSearch(DEMO_SEARCH)


def build(s: Settings) -> tuple[LLM, Searcher]:
    if s.demo:
        return build_demo()
    llm = OpenAICompatLLM(s.llm_base_url.strip(), s.llm_api_key.strip(), s.llm_model.strip())
    key = s.search_api_key.strip()
    if s.search_provider == "博查" and key:
        return llm, BochaSearch(key)
    if s.search_provider == "Tavily" and key:
        return llm, TavilySearch(key)
    return llm, NoSearch()


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def save_env(s: Settings, path: Path = ENV_PATH) -> None:
    """把设置写进项目文件夹的 .env，下次打开自动读取。.env 已在 .gitignore 里，不会传到 GitHub。"""
    lines = [
        "# 先别做的本机设置。这个文件不会上传到 GitHub。",
        f"LLM_BASE_URL={s.llm_base_url}",
        f"LLM_MODEL={s.llm_model}",
        f"LLM_API_KEY={s.llm_api_key}",
        f"SEARCH_PROVIDER={s.search_provider}",
        f"SEARCH_API_KEY={s.search_api_key}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for k, v in [("LLM_BASE_URL", s.llm_base_url), ("LLM_MODEL", s.llm_model), ("LLM_API_KEY", s.llm_api_key),
                 ("SEARCH_PROVIDER", s.search_provider), ("SEARCH_API_KEY", s.search_api_key)]:
        os.environ[k] = v
