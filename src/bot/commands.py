"""命令类系统"""

from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

from aiogram.types import Message


@dataclass
class Command:
    """命令类定义"""

    name: str  # 命令名称（如 "group_authorize"）
    description: str  # 命令描述
    usage: str  # 使用说明（用于参数错误时提示用户）
    required_role: str  # 所需权限：'super_admin' | 'group_admin' | 'user'
    allowed_chat_types: List[
        str
    ]  # 允许使用的场景：['private'] | ['group'] | ['private', 'group']
    handler: Callable[[Message], Awaitable[None]]  # 命令处理函数（异步）


class CommandRegistry:
    """命令注册表"""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """注册命令"""
        self._commands[command.name] = command

    def get(self, name: str) -> Optional[Command]:
        """获取命令"""
        return self._commands.get(name)

    def list_all(self) -> List[Command]:
        """列出所有命令"""
        return list(self._commands.values())

    def exists(self, name: str) -> bool:
        """检查命令是否存在"""
        return name in self._commands


# 全局命令注册表实例
command_registry = CommandRegistry()
