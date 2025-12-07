# TelePal

基于 LangGraph 的 Telegram AI 助手，支持长期记忆、网络搜索和多用户权限管理。

## 功能特性

- **AI 对话** - 基于 OpenAI 兼容 API，支持上下文记忆
- **长期记忆** - 使用向量数据库存储用户偏好和重要信息
- **网络搜索** - 集成 Tavily Search，获取实时信息
- **网页抓取** - 抓取并解析网页内容
- **权限管理** - 超管、群管、白名单三级权限体系
- **群组支持** - 支持私聊和群组，群组需 @ 或回复触发

## 技术栈

- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot 框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent 编排
- [PostgreSQL](https://www.postgresql.org/) - 对话历史和权限存储
- [Tavily](https://tavily.com/) - 网络搜索（可选）

## 快速开始

### 环境要求

- Python >= 3.11
- PostgreSQL >= 14
- [uv](https://github.com/astral-sh/uv) 包管理器（推荐）

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/TelePal.git
cd TelePal

# 安装依赖
uv sync
```

### 创建 Telegram Bot

1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather) 并打开对话
2. 发送 `/newbot` 命令
3. 按提示输入机器人名称（显示名）和用户名（以 `_bot` 结尾）
4. 创建成功后会收到 Bot Token，格式如 `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置
vim .env
```

必填配置项：
- `TELEGRAM_BOT_TOKEN` - 上一步获取的 Bot Token
- `POSTGRES_*` - 数据库连接信息
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` - LLM 配置
- `EMBEDDING_*` - 嵌入模型配置（用于长期记忆）
- `INITIAL_SUPER_ADMINS` - 初始超管的 Telegram User ID

可选配置：
- `TAVILY_API_KEY` - 启用网络搜索功能

### 运行

```bash
# 使用启动脚本
./bot.sh start

# 查看状态
./bot.sh status

# 查看日志
./bot.sh logs

# 停止
./bot.sh stop
```

或直接运行：

```bash
uv run python main.py
```

## 命令列表

### 超管命令（仅私聊）

| 命令 | 说明 |
|------|------|
| `/group_authorize <chat_id>` | 授权群组 |
| `/group_revoke <chat_id>` | 撤销群组授权 |
| `/group_list` | 查看已授权群组 |
| `/permission_set <user_id> <role>` | 设置用户权限 |

### 管理命令（私聊和群组）

| 命令 | 说明 |
|------|------|
| `/whitelist_add <user_id> [type] [chat_id]` | 添加白名单 |
| `/whitelist_remove <user_id> [type] [chat_id]` | 移除白名单 |
| `/whitelist_list [type] [chat_id]` | 查看白名单 |

### 普通命令

| 命令 | 说明 |
|------|------|
| `/memory_list [query]` | 查看长期记忆 |
| `/memory_delete <key>` | 删除记忆 |

## 项目结构

```
TelePal/
├── main.py              # 入口
├── bot.sh               # 启动脚本
├── .env.example         # 配置模板
├── src/
│   ├── agent/           # LangGraph Agent
│   │   ├── graph.py     # Graph 定义
│   │   ├── prompts.py   # 系统提示词
│   │   └── state.py     # 状态定义
│   ├── auth/            # 权限系统
│   │   ├── database.py  # 权限数据库操作
│   │   ├── models.py    # 数据模型
│   │   └── service.py   # 权限检查服务
│   ├── bot/             # Telegram Bot
│   │   ├── handlers.py  # 消息处理
│   │   ├── admin_handlers.py  # 管理命令
│   │   ├── commands.py  # 命令注册
│   │   └── middleware.py
│   └── utils/
│       ├── db/          # 数据库连接
│       ├── tools/       # Agent 工具
│       ├── logger.py
│       └── settings.py
└── logs/                # 日志目录
```

## License

MIT

