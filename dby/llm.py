"""大模型接入。兼容所有 OpenAI 格式的接口（DeepSeek、通义、Kimi、OpenAI 等）。"""

from __future__ import annotations

import copy
import json
import re
from typing import Protocol

from .prompts import SYSTEM


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    name: str

    def json(self, task: str, prompt: str) -> dict: ...


def _parse(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no json object")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("json is not an object")
    return data


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 90):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.model = model
        self.name = model

    def json(self, task: str, prompt: str) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ]
        last_err: Exception | None = None
        for _ in range(2):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                return _parse(resp.choices[0].message.content or "")
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
                messages.append({"role": "user", "content": "上一次输出不是合法 JSON，请只输出 JSON 对象。"})
            except Exception as e:  # 网络、鉴权、额度等
                raise LLMError(f"调用 {self.model} 失败：{e}") from e
        raise LLMError(f"{self.model} 连续两次没有返回合法 JSON（{last_err}）")


class DemoLLM:
    """演示模式：不需要 API Key，返回预置的"自我验证"案例数据。"""

    name = "演示数据"

    def __init__(self, responses: dict[str, dict]):
        self.responses = responses

    def json(self, task: str, prompt: str) -> dict:
        if task not in self.responses:
            raise LLMError(f"演示数据里没有 {task}")
        return copy.deepcopy(self.responses[task])
