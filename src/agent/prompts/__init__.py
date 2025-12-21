"""提示词模板模块 - 使用 Jinja2 渲染"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

# 模板目录路径
_template_dir = Path(__file__).parent

_jinja_env = Environment(
    loader=FileSystemLoader(str(_template_dir)),
    # 禁用 HTML 转义
    autoescape=False,
    # 去除块前后的空白
    trim_blocks=True,
    # 去除块左侧的空白
    lstrip_blocks=True,
)


def get_template(name: str) -> Template:
    """
    获取模板对象

    Args:
        name: 模板文件名（不含扩展名，会自动添加 .j2）

    Returns:
        Jinja2 Template 对象
    """
    return _jinja_env.get_template(f"{name}.j2")


def render_supervisor_prompt(chat_type: str = "private", user_id: int = 0) -> str:
    """
    渲染 supervisor 提示词模板

    Args:
        chat_type: 聊天类型
        user_id: 用户 ID

    Returns:
        渲染后的提示词字符串
    """
    template = get_template("supervisor")
    return template.render(chat_type=chat_type, user_id=user_id)
