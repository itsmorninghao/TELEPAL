"""网页抓取工具"""

import aiohttp
from bs4 import BeautifulSoup
from langchain_core.tools import tool


async def _scrape_webpage_impl(url: str, max_length: int = 2000) -> str:
    """抓取网页内容，返回纯文本"""
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
        return f"抓取网页时发生错误：{str(e)}"


@tool
async def scrape_webpage(url: str, max_length: int = 2000) -> str:
    """抓取网页内容

    Args:
        url: 网页 URL
        max_length: 最大内容长度（默认 2000）
    """
    return await _scrape_webpage_impl(url, max_length)


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(_scrape_webpage_impl("https://www.baidu.com")))
