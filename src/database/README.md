# 数据库模块 (src/database)

本模块统一管理所有数据库相关操作，采用分层架构设计。

## 架构说明

本模块采用双连接池策略：
- **SQLAlchemy** (`engine.py`) - 用于业务表的 ORM 操作
- **psycopg** (`langgraph_pool.py`) - 用于 LangGraph 组件（LangGraph 要求使用原生 psycopg_pool，不兼容 SQLAlchemy）

```
src/database/
├── __init__.py           # 统一导出接口
├── engine.py             # SQLAlchemy 异步引擎配置（业务表）
├── langgraph_pool.py     # LangGraph 专用 psycopg 连接池
├── models.py             # SQLAlchemy ORM 模型定义
├── init_db.py            # 数据库初始化脚本
├── README.md             # 本文档
├── langgraph/            # LangGraph 存储
│   ├── __init__.py
│   ├── checkpointer.py   # AsyncPostgresSaver（对话记忆）
│   └── store.py          # AsyncPostgresStore（长期记忆/向量存储）
└── repositories/         # 业务数据访问层
    ├── __init__.py
    ├── auth.py           # 认证相关（权限、白名单、群组授权）
    └── profiles.py       # 用户资料（位置、时区）
```

## 模块职责

| 文件 | 职责 |
|------|------|
| `engine.py` | SQLAlchemy 异步引擎单例，提供 `get_session()` 上下文管理器 |
| `langgraph_pool.py` | psycopg 连接池管理，供 LangGraph 组件使用 |
| `models.py` | ORM 模型定义，每个模型提供 `to_domain()` 方法转换为领域模型 |
| `init_db.py` | 数据库表初始化脚本 |

## 开发计划
- [x] 目前数据库初始化的方式太不优雅了，调研更加优雅的初始化方式