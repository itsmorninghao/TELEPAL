"""获取用户时间工具"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

from src.bot import user_id_context
from src.database.repositories import profiles

logger = logging.getLogger(__name__)


@tool
async def get_user_time() -> str:
    """获取当前用户所在时区的准确时间信息"""
    # 从上下文获取 user_id
    user_id = user_id_context.get()

    # 获取用户位置信息
    user_location = await profiles.get_user_location(user_id)

    if user_location and user_location.get("timezone"):
        try:
            timezone_str = user_location["timezone"]
            tz = ZoneInfo(timezone_str)
            now = datetime.now(tz)

            period = ["凌晨", "早上", "下午", "晚上"][now.hour // 6]
            weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][
                now.weekday()
            ]

            return f"""【用户所在地当前时间 - {timezone_str}】

这是当前用户所在时区（{timezone_str}）的准确时间：
- 时间: {now.strftime("%H:%M")}
- 时段: {period}
- 日期: {now.strftime("%Y-%m-%d")} ({weekday})

重要提示：
1. 这是**当前用户所在地的准确时间**，回答用户关于时间的问题时，必须使用这个时间
2. 每次调用此工具时，时间信息都会自动更新为最新值"""
        except Exception as e:
            logger.warning(f"获取用户时区时间时出错: {e}")
            # 降级到 UTC
            now_utc = datetime.now(ZoneInfo("UTC"))
            return f"""【当前时间 - UTC（时区解析失败）】

注意：无法解析用户设置的时区，以下为 UTC 标准时间：
- 时间: {now_utc.strftime("%H:%M")} (UTC)
- 日期: {now_utc.strftime("%Y-%m-%d")}

提示：此 UTC 时间可能与用户实际所在地时间有偏差"""
    else:
        # 未设置时区时，返回 UTC 时间
        now_utc = datetime.now(ZoneInfo("UTC"))
        return f"""【当前时间 - UTC（用户未设置时区）】

注意：当前用户未设置时区信息，以下为 UTC 标准时间：
- 时间: {now_utc.strftime("%H:%M")} (UTC)
- 日期: {now_utc.strftime("%Y-%m-%d")}

重要提示：
1. 由于用户未设置时区，此 UTC 时间可能与用户实际所在地时间有较大偏差
2. 如果用户询问时间，建议温和引导用户设置时区以获得准确时间"""
