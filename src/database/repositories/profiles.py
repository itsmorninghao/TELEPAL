"""用户资料数据库操作"""

from typing import Any, Optional

from sqlalchemy import select

from src.database.engine import get_session
from src.database.models import UserProfileModel


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
    async with get_session() as session:
        # 查询是否存在
        stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            # 更新现有记录
            model.latitude = latitude
            model.longitude = longitude
            model.timezone = timezone
        else:
            # 创建新记录
            model = UserProfileModel(
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
            )
            session.add(model)

        await session.flush()
        return True


async def get_user_location(user_id: int) -> Optional[dict[str, Any]]:
    """获取用户位置信息

    Args:
        user_id: 用户 ID

    Returns:
        包含位置信息的字典，如果不存在则返回 None
    """
    async with get_session() as session:
        stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return {
                "user_id": model.user_id,
                "latitude": model.latitude,
                "longitude": model.longitude,
                "timezone": model.timezone,
                "location_updated_at": model.location_updated_at,
                "created_at": model.created_at,
            }
        return None
