"""Web tools: web_search and web_fetch."""

import html
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

from nanobot.agent.tools.base import Tool

# Shared constants
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
MAX_REDIRECTS = 5  # Limit redirects to prevent DoS attacks


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.I)
    text = re.sub(r'<style[\s\S]*?</style>', '', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()


def _normalize(text: str) -> str:
    """Normalize whitespace."""
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate URL: must be http(s) with valid domain."""
    try:
        p = urlparse(url)
        if p.scheme not in ('http', 'https'):
            return False, f"Only http/https allowed, got '{p.scheme or 'none'}'"
        if not p.netloc:
            return False, "Missing domain"
        return True, ""
    except Exception as e:
        return False, str(e)


class WebSearchTool(Tool):
    """Search the web using Brave Search API."""

    name = "web_search"
    description = "Search the web. Returns titles, URLs, and snippets."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {"type": "integer", "description": "Results (1-10)", "minimum": 1, "maximum": 10}
        },
        "required": ["query"]
    }

    def __init__(self, api_key: str | None = None, max_results: int = 5, proxy: str | None = None):
        self._init_api_key = api_key
        self.max_results = max_results
        self.proxy = proxy

    @property
    def api_key(self) -> str:
        """Resolve API key at call time so env/config changes are picked up."""
        return self._init_api_key or os.environ.get("BOCHA_API_KEY", "")

    async def execute(self, query: str, count: int | None = None, **kwargs: Any) -> str:
        # 检查是否配置了 API 密钥
        if not self.api_key:
            # 如果未配置，返回错误提示信息
            return (
                # 提示配置 Bocha Search API 密钥
                "Error: Bocha Search API key not configured. Set it in "
                # 说明配置文件路径
                "~/.nanobot/config.json under tools.web.search.apiKey "
                # 说明环境变量，并提示重启
                "(or export BOCHA_API_KEY), then restart the gateway."
            )

        # 开始异常捕获块
        try:
            # 限制返回结果的数量在 1 到 10 之间
            n = min(max(count or self.max_results, 1), 10)
            # 记录日志，说明是否启用了代理
            logger.debug("WebSearch: {}", "proxy enabled" if self.proxy else "direct connection")
            
            # 准备请求目标 URL
            url = "https://api.bocha.cn/v1/web-search"
            # 构造 JSON 格式的请求体数据
            payload = {"query": query, "summary": True, "count": n}
            # 构造请求头，包含认证信息和内容类型
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            
            # 使用 httpx 创建异步客户端实例，并配置代理
            async with httpx.AsyncClient(proxy=self.proxy) as client:
                # 发送 POST 异步请求，传入 url、headers、json 和超时时间
                r = await client.post(url, headers=headers, json=payload, timeout=10.0)
                # 如果响应状态码不是 2xx，抛出 HTTP 异常
                r.raise_for_status()

            # 解析响应的 JSON 数据
            response_data = r.json()
            
            # 检查业务状态码是否为 200，防止请求失败
            if response_data.get("code") != 200:
                # 提取错误信息，默认为未知错误
                error_msg = response_data.get("msg") or "Unknown API Error"
                # 返回错误提示给调用方
                return f"API Error: {error_msg}"
                
            # 获取数据字段，默认为空字典
            data = response_data.get("data", {})
            # 尝试获取网页结果对象，默认为空字典
            web_pages = data.get("webPages", {})
            # 从 webPages 中获取 value 列表，或者退化为从 data 获取 results
            results = web_pages.get("value", data.get("results", []))
            # 截取前 n 个结果，避免超过限制
            results = results[:n]
            
            # 检查结果列表是否为空
            if not results:
                # 如果为空，返回没有找到结果的提示
                return f"No results for: {query}"

            # 初始化用于存储格式化结果的字符串列表
            lines = [f"Results for: {query}\n"]
            # 遍历搜索结果列表，带上索引
            for i, item in enumerate(results, 1):
                # 提取标题，优先取 name，没有则取 title
                title = item.get("name") or item.get("title", "")
                # 将标题和 URL 拼接到列表中
                lines.append(f"{i}. {title}\n   {item.get('url', '')}")
                # 提取描述，优先取 summary，没有则取 snippet 或 description
                desc = item.get("summary") or item.get("snippet") or item.get("description")
                # 检查描述是否存在
                if desc:
                    # 如果有描述信息，则添加到列表中
                    lines.append(f"   {desc}")
            # 将列表中的字符串用换行符连接并返回
            return "\n".join(lines)
        # 捕获代理错误异常
        except httpx.ProxyError as e:
            # 记录代理错误的日志
            logger.error("WebSearch proxy error: {}", e)
            # 返回代理错误信息
            return f"Proxy error: {e}"
        # 捕获其他所有异常
        except Exception as e:
            # 记录通用错误的日志
            logger.error("WebSearch error: {}", e)
            # 返回通用错误信息
            return f"Error: {e}"



class WebFetchTool(Tool):
    """Fetch and extract content from a URL using Readability."""

    name = "web_fetch"
    description = "Fetch URL and extract readable content (HTML → markdown/text)."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "extractMode": {"type": "string", "enum": ["markdown", "text"], "default": "markdown"},
            "maxChars": {"type": "integer", "minimum": 100}
        },
        "required": ["url"]
    }

    def __init__(self, max_chars: int = 50000, proxy: str | None = None):
        self.max_chars = max_chars
        self.proxy = proxy

    async def execute(self, url: str, extractMode: str = "markdown", maxChars: int | None = None, **kwargs: Any) -> str:
        from readability import Document

        max_chars = maxChars or self.max_chars
        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            return json.dumps({"error": f"URL validation failed: {error_msg}", "url": url}, ensure_ascii=False)

        try:
            logger.debug("WebFetch: {}", "proxy enabled" if self.proxy else "direct connection")
            async with httpx.AsyncClient(
                follow_redirects=True,
                max_redirects=MAX_REDIRECTS,
                timeout=30.0,
                proxy=self.proxy,
            ) as client:
                r = await client.get(url, headers={"User-Agent": USER_AGENT})
                r.raise_for_status()

            ctype = r.headers.get("content-type", "")

            if "application/json" in ctype:
                text, extractor = json.dumps(r.json(), indent=2, ensure_ascii=False), "json"
            elif "text/html" in ctype or r.text[:256].lower().startswith(("<!doctype", "<html")):
                doc = Document(r.text)
                content = self._to_markdown(doc.summary()) if extractMode == "markdown" else _strip_tags(doc.summary())
                text = f"# {doc.title()}\n\n{content}" if doc.title() else content
                extractor = "readability"
            else:
                text, extractor = r.text, "raw"

            truncated = len(text) > max_chars
            if truncated: text = text[:max_chars]

            return json.dumps({"url": url, "finalUrl": str(r.url), "status": r.status_code,
                              "extractor": extractor, "truncated": truncated, "length": len(text), "text": text}, ensure_ascii=False)
        except httpx.ProxyError as e:
            logger.error("WebFetch proxy error for {}: {}", url, e)
            return json.dumps({"error": f"Proxy error: {e}", "url": url}, ensure_ascii=False)
        except Exception as e:
            logger.error("WebFetch error for {}: {}", url, e)
            return json.dumps({"error": str(e), "url": url}, ensure_ascii=False)

    def _to_markdown(self, html: str) -> str:
        """Convert HTML to markdown."""
        # Convert links, headings, lists before stripping tags
        text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
                      lambda m: f'[{_strip_tags(m[2])}]({m[1]})', html, flags=re.I)
        text = re.sub(r'<h([1-6])[^>]*>([\s\S]*?)</h\1>',
                      lambda m: f'\n{"#" * int(m[1])} {_strip_tags(m[2])}\n', text, flags=re.I)
        text = re.sub(r'<li[^>]*>([\s\S]*?)</li>', lambda m: f'\n- {_strip_tags(m[1])}', text, flags=re.I)
        text = re.sub(r'</(p|div|section|article)>', '\n\n', text, flags=re.I)
        text = re.sub(r'<(br|hr)\s*/?>', '\n', text, flags=re.I)
        return _normalize(_strip_tags(text))
