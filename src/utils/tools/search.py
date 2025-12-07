"""Tavily 搜索工具"""

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
