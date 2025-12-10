"""用户资料数据库操作"""

from typing import Any, Dict, Optional

from src.database.connection import get_pool


async def save_user_location(
    user_id: int,
    latitude: float,
    longitude: float,
    timezone: Optional[str] = None,
) -> bool:
    """保存用户位置信息到数据库

    Args:
        user_id: 用户 ID
        latitude: 纬度
        longitude: 经度
        timezone: 时区（可选）

    Returns:
        是否保存成功
    """
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


async def get_user_location(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户位置信息

    Args:
        user_id: 用户 ID

    Returns:
        包含位置信息的字典，如果不存在则返回 None
    """
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

