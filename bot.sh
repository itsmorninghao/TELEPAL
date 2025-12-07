#!/bin/bash

# Telegram 机器人启动脚本
# 支持：启动、状态、停止、重启

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bot.log"
PID_FILE="$LOG_DIR/bot.pid"

MAIN_SCRIPT="$SCRIPT_DIR/main.py"
PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python3"


# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 确保日志目录存在
ensure_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
    fi
}

# 查找实际运行的进程 PID
find_running_pid() {
    # 方法1: 检查 PID 文件
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            # 验证这个进程确实是我们的 bot
            if ps -p "$PID" -o command= | grep -q "main.py"; then
                echo "$PID"
                return 0
            fi
        fi
        # PID 文件存在但进程不存在或不是我们的进程，清理 PID 文件
        rm -f "$PID_FILE"
    fi
    
    # # 方法2: 通过进程名查找,查找运行 main.py 的进程
    # FOUND_PID=$(pgrep -f "python.*main.py" | head -n 1)
    # if [ -n "$FOUND_PID" ] && ps -p "$FOUND_PID" > /dev/null 2>&1; then
    #     # 验证进程确实在运行我们的脚本
    #     if ps -p "$FOUND_PID" -o command= | grep -q "main.py"; then
    #         echo "$FOUND_PID"
    #         # 更新 PID 文件以保持同步
    #         echo "$FOUND_PID" > "$PID_FILE"
    #         return 0
    #     fi
    # fi
    
    return 1
}

# 检查进程是否运行
is_running() {
    PID=$(find_running_pid)
    if [ -n "$PID" ]; then
        return 0
    else
        return 1
    fi
}

# 启动函数
start() {
    if is_running; then
        PID=$(find_running_pid)
        echo -e "${YELLOW}机器人已经在运行中 (PID: $PID)${NC}"
        echo -e "${YELLOW}提示: 如果这是通过其他方式启动的进程，请先停止它${NC}"
        return 1
    fi

    if [ ! -f "$MAIN_SCRIPT" ]; then
        echo -e "${RED}错误: 找不到主程序文件 $MAIN_SCRIPT${NC}"
        return 1
    fi

    # 确保日志目录存在
    ensure_log_dir

    echo -e "${GREEN}正在启动机器人...${NC}"
    
    # 使用 nohup 后台运行，日志追加模式
    cd "$SCRIPT_DIR"
    nohup $PYTHON_CMD "$MAIN_SCRIPT" >> "$LOG_FILE" 2>&1 &
    PID=$!
    
    # 保存 PID
    echo $PID > "$PID_FILE"
    
    # 等待一下确认启动
    sleep 2
    
    if is_running; then
        echo -e "${GREEN}✓ 机器人启动成功！${NC}"
        echo -e "  PID: $PID"
        echo -e "  日志文件: $LOG_FILE"
        echo -e "  查看日志: tail -f $LOG_FILE"
    else
        echo -e "${RED}✗ 机器人启动失败，请检查日志: $LOG_FILE${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 停止函数
stop() {
    if ! is_running; then
        echo -e "${YELLOW}机器人未运行${NC}"
        return 1
    fi

    PID=$(find_running_pid)
    echo -e "${YELLOW}正在停止机器人 (PID: $PID)...${NC}"
    
    # 尝试优雅停止
    kill "$PID" 2>/dev/null
    
    # 等待进程结束
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # 如果还在运行，强制杀死
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}进程未响应，强制停止...${NC}"
        kill -9 "$PID" 2>/dev/null
        sleep 1
    fi
    
    # 清理 PID 文件
    rm -f "$PID_FILE"
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 机器人已停止${NC}"
    else
        echo -e "${RED}✗ 停止失败${NC}"
        return 1
    fi
}

# 状态函数
status() {
    if is_running; then
        PID=$(find_running_pid)
        echo -e "${GREEN}✓ 机器人正在运行${NC}"
        echo -e "  PID: $PID"
        echo -e "  启动时间: $(ps -o lstart= -p $PID 2>/dev/null || echo '未知')"
        echo -e "  内存使用: $(ps -o rss= -p $PID 2>/dev/null | awk '{printf "%.2f MB", $1/1024}')"
        echo -e "  日志文件: $LOG_FILE"
    else
        echo -e "${RED}✗ 机器人未运行${NC}"
        return 1
    fi
}

# 重启函数
restart() {
    echo -e "${YELLOW}正在重启机器人...${NC}"
    stop
    sleep 2
    start
}

# 查看日志
logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}日志文件不存在: $LOG_FILE${NC}"
    fi
}

# 主函数
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动机器人"
        echo "  stop    - 停止机器人"
        echo "  restart - 重启机器人"
        echo "  status  - 查看运行状态"
        echo "  logs    - 实时查看日志"
        exit 1
        ;;
esac

exit $?