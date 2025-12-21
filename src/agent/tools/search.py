"""搜索和网页抓取工具"""

import aiohttp
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from tavily import TavilyClient

from src.utils.settings import setting


@tool
async def tavily_search(query: str, max_results: int = 5) -> str:
    """使用 Tavily 搜索网络信息

    Args:
        query: 搜索查询
        max_results: 最大返回结果数（默认 5）
    """
    api_key = setting.TAVILY_API_KEY
    if not api_key:
        return "错误：TAVILY_API_KEY 环境变量未设置"

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )

        if not response.get("results"):
            return f"未找到关于 '{query}' 的搜索结果"

        # 格式化搜索结果
        results = []
        for idx, result in enumerate(response["results"], 1):
            title = result.get("title", "无标题")
            url = result.get("url", "")
            content = result.get("content", "")

            results.append(
                f"{idx}. {title}\n   链接: {url}\n   内容: {content[:200]}..."
                if len(content) > 200
                else f"   内容: {content}"
            )

        return "\n\n".join(results)

    except Exception as e:
        return f"搜索时发生错误: {str(e)}"


async def _scrape_webpage_impl(url: str, max_length: int = 2000) -> str:
    """简单爬虫"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    return f"错误：无法访问网页，状态码: {response.status}"

                html = await response.text()

        # 使用 BeautifulSoup 解析
        soup = BeautifulSoup(html, "html.parser")

        # 移除脚本和样式标签
        for script in soup(["script", "style"]):
            script.decompose()

        # 提取文本内容
        text = soup.get_text()

        # 清理空白字符
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        # 截断到最大长度
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text if text else "无法提取网页内容"

    except aiohttp.ClientError as e:
        return f"网络错误：{str(e)}"
    except Exception as e:
        return f"抓取网页时发生错误: {str(e)}"


@tool
async def scrape_webpage(url: str, max_length: int = 2000) -> str:
    """抓取网页内容

    Args:
        url: 网页 URL
        max_length: 最大内容长度（默认 2000）
    """
    return await _scrape_webpage_impl(url, max_length)
