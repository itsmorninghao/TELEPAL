"""日志配置模块"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.utils.settings import setting


def setup_logger() -> logging.Logger:
    """配置日志记录器"""
    root_logger = logging.getLogger()

    # 防止重复添加处理器
    if root_logger.handlers:
        return root_logger

    log_level = setting.LOG_LEVEL.upper()

    # 创建 logs 目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 配置日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件处理器
    file_handler = RotatingFileHandler(
        "logs/telepal.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # 配置根日志记录器
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger
