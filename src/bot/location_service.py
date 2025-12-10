"""用户位置服务"""

import logging
from typing import Optional

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from timezonefinder import TimezoneFinder

from src.utils.db.connection import get_pool

logger = logging.getLogger(__name__)

_timezone_finder = TimezoneFinder()


async def get_timezone_from_location(latitude: float, longitude: float) -> str:
    """根据经纬度获取时区
    
    使用 timezonefinder 获取准确的时区信息
    
    Args:
        latitude: 纬度
        longitude: 经度
        
    Returns:
        时区字符串（如 'Asia/Shanghai'），如果获取失败则返回 None
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
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO user_profiles (user_id, latitude, longitude, timezone, location_updated_at, created_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        timezone = EXCLUDED.timezone,
                        location_updated_at = NOW()
                    """,
                    (user_id, latitude, longitude, timezone),
                )
                return True

    except Exception as e:
        logger.error(f"保存用户位置信息时发生错误: {e}", exc_info=True)
        return False


async def get_user_location(user_id: int) -> Optional[dict]:
    """获取用户位置信息
    
    Args:
        user_id: 用户 ID
        
    Returns:
        包含位置信息的字典，如果不存在则返回 None
    """
    try:
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id, latitude, longitude, timezone, location_updated_at, created_at
                    FROM user_profiles
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = await cur.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "latitude": row[1],
                        "longitude": row[2],
                        "timezone": row[3],
                        "location_updated_at": row[4],
                        "created_at": row[5],
                    }
                return None
    except Exception as e:
        logger.error(f"获取用户位置信息时发生错误: {e}", exc_info=True)
        return None

