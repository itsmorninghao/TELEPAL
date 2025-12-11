"""用户权限数据库操作"""

from typing import Any, Dict, List, Optional

from src.auth.models import (
    AuthorizedGroup,
    UserPermission,
    UserRole,
    WhitelistEntry,
)
from src.database.connection import get_pool


def _row_to_dict(row, cursor) -> Optional[Dict[str, Any]]:
    """将 psycopg cursor 的行转换为字典"""
    if row is None:
        return None
    return {desc[0]: val for desc, val in zip(cursor.description, row)}


# ==================== 用户权限操作 ====================


async def get_user_permission(user_id: int) -> Optional[UserPermission]:
    """获取用户权限"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM user_permissions WHERE user_id = %s",
                (user_id,),
            )
            row = await cur.fetchone()
            if row:
                row_dict = _row_to_dict(row, cur)
                return UserPermission.from_db_row(row_dict)
            return None


async def is_super_admin(user_id: int) -> bool:
    """检查用户是否为超管"""
    permission = await get_user_permission(user_id)
    return permission is not None and permission.role == UserRole.SUPER_ADMIN


async def set_user_permission(user_id: int, role: UserRole) -> UserPermission:
    """设置用户权限"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_permissions (user_id, role)
                VALUES (%s, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET role = %s, updated_at = NOW()
                RETURNING *
                """,
                (user_id, role.value, role.value),
            )
            row = await cur.fetchone()
            row_dict = _row_to_dict(row, cur)
            return UserPermission.from_db_row(row_dict)


async def delete_user_permission(user_id: int) -> bool:
    """删除用户权限"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM user_permissions WHERE user_id = %s",
                (user_id,),
            )
            return cur.rowcount == 1


# ==================== 群组授权操作 ====================


async def is_group_authorized(chat_id: int) -> bool:
    """检查群组是否已授权"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id FROM authorized_groups 
                WHERE chat_id = %s AND is_active = TRUE
                """,
                (chat_id,),
            )
            row = await cur.fetchone()
            return row is not None


async def get_authorized_group(chat_id: int) -> Optional[AuthorizedGroup]:
    """获取授权群组信息"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM authorized_groups WHERE chat_id = %s",
                (chat_id,),
            )
            row = await cur.fetchone()
            if row:
                row_dict = _row_to_dict(row, cur)
                return AuthorizedGroup.from_db_row(row_dict)
            return None


async def authorize_group(
    chat_id: int, chat_title: Optional[str], authorized_by: int
) -> AuthorizedGroup:
    """授权群组"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO authorized_groups (chat_id, chat_title, authorized_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_id) 
                DO UPDATE SET 
                    chat_title = COALESCE(EXCLUDED.chat_title, authorized_groups.chat_title),
                    is_active = TRUE,
                    authorized_at = NOW()
                RETURNING *
                """,
                (chat_id, chat_title, authorized_by),
            )
            row = await cur.fetchone()
            row_dict = _row_to_dict(row, cur)
            return AuthorizedGroup.from_db_row(row_dict)


async def revoke_group_authorization(chat_id: int) -> bool:
    """撤销群组授权"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE authorized_groups 
                SET is_active = FALSE 
                WHERE chat_id = %s
                """,
                (chat_id,),
            )
            return cur.rowcount == 1


async def list_authorized_groups() -> List[AuthorizedGroup]:
    """列出所有已授权的群组"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM authorized_groups WHERE is_active = TRUE ORDER BY authorized_at DESC"
            )
            rows = await cur.fetchall()
            return [AuthorizedGroup.from_db_row(_row_to_dict(row, cur)) for row in rows]


# ==================== 白名单操作 ====================


async def is_user_whitelisted(
    user_id: int, chat_type: str, chat_id: Optional[int] = None
) -> bool:
    """检查用户是否在白名单中"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id FROM whitelist 
                WHERE user_id = %s AND chat_type = %s AND chat_id IS NOT DISTINCT FROM %s
                """,
                (user_id, chat_type, chat_id),
            )
            row = await cur.fetchone()
            return row is not None


async def add_to_whitelist(
    user_id: int,
    chat_type: str,
    chat_id: Optional[int],
    created_by: Optional[int] = None,
) -> WhitelistEntry:
    """添加用户到白名单"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO whitelist (user_id, chat_type, chat_id, created_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, chat_type, chat_id) DO NOTHING
                RETURNING *
                """,
                (user_id, chat_type, chat_id, created_by),
            )
            row = await cur.fetchone()
            if row:
                row_dict = _row_to_dict(row, cur)
                return WhitelistEntry.from_db_row(row_dict)
            # 如果已存在，返回现有记录
            await cur.execute(
                """
                SELECT * FROM whitelist 
                WHERE user_id = %s AND chat_type = %s AND chat_id IS NOT DISTINCT FROM %s
                """,
                (user_id, chat_type, chat_id),
            )
            row = await cur.fetchone()
            row_dict = _row_to_dict(row, cur)
            return WhitelistEntry.from_db_row(row_dict)


async def remove_from_whitelist(
    user_id: int, chat_type: str, chat_id: Optional[int] = None
) -> bool:
    """从白名单中移除用户"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                DELETE FROM whitelist 
                WHERE user_id = %s AND chat_type = %s AND chat_id IS NOT DISTINCT FROM %s
                """,
                (user_id, chat_type, chat_id),
            )
            return cur.rowcount == 1


async def list_whitelist(
    chat_type: Optional[str] = None, chat_id: Optional[int] = None
) -> List[WhitelistEntry]:
    """列出白名单，可按 chat_type 和 chat_id 过滤"""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if chat_type and chat_id is not None:
                await cur.execute(
                    """
                    SELECT * FROM whitelist 
                    WHERE chat_type = %s AND chat_id = %s
                    ORDER BY created_at DESC
                    """,
                    (chat_type, chat_id),
                )
            elif chat_type:
                await cur.execute(
                    """
                    SELECT * FROM whitelist 
                    WHERE chat_type = %s
                    ORDER BY created_at DESC
                    """,
                    (chat_type,),
                )
            else:
                await cur.execute("SELECT * FROM whitelist ORDER BY created_at DESC")
            rows = await cur.fetchall()
            return [WhitelistEntry.from_db_row(_row_to_dict(row, cur)) for row in rows]
