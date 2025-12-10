"""用户位置服务（业务逻辑层）"""

import logging
from typing import Any, Dict, Optional

from timezonefinder import TimezoneFinder

from src.database.repositories import profiles

logger = logging.getLogger(__name__)

_timezone_finder = TimezoneFinder()


async def get_timezone_from_location(latitude: float, longitude: float) -> str:
    """根据经纬度获取时区

    使用 timezonefinder 获取准确的时区信息

    Args:
        latitude: 纬度
        longitude: 经度

    Returns:
        时区字符串（如 'Asia/Shanghai'），如果获取失败则返回 'Unknown'
    """
    try:
        # 使用 timezonefinder 获取准确的时区
        return _timezone_finder.timezone_at(lng=longitude, lat=latitude)

    except Exception as e:
        logger.error(f"获取时区时发生错误: {e}", exc_info=True)
        return "Unknown"


async def save_user_location(
    user_id: int, latitude: float, longitude: float, timezone: Optional[str] = None
) -> bool:
    """保存用户位置信息到数据库

    Args:
        user_id: 用户 ID
        latitude: 纬度
        longitude: 经度
        timezone: 时区（可选，如果不提供则自动获取）

    Returns:
        是否保存成功
    """
    try:
        return await profiles.save_user_location(user_id, latitude, longitude, timezone)
    except Exception as e:
        logger.error(f"保存用户位置信息时发生错误: {e}", exc_info=True)
        return False


async def get_user_location(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户位置信息

    Args:
        user_id: 用户 ID

    Returns:
        包含位置信息的字典，如果不存在则返回 None
    """
    try:
        return await profiles.get_user_location(user_id)
    except Exception as e:
        logger.error(f"获取用户位置信息时发生错误: {e}", exc_info=True)
        return None
