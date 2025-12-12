# 数据库模块 (src/database)

本模块统一管理所有数据库相关操作，采用分层架构设计。

```
src/database/
├── __init__.py           # 统一导出接口
├── connection.py         # PostgreSQL 连接池管理
├── init_db.py           # 数据库初始化脚本
├── README.md            # 本文档
├── langgraph/           # LangGraph 存储
│   ├── __init__.py
│   ├── checkpointer.py  # AsyncPostgresSaver（对话记忆）
│   └── store.py         # AsyncPostgresStore（长期记忆/向量存储）
└── repositories/        # 业务数据访问层
    ├── __init__.py
    ├── auth.py          # 认证相关（权限、白名单、群组授权）
    └── profiles.py      # 用户资料（位置、时区）
```

## 开发计划
- [x] 目前数据库初始化的方式太不优雅了，调研更加优雅的初始化方式