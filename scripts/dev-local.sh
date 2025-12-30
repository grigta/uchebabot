#!/bin/bash

# Local development script (without tunnel)
# For when you don't need external webhook/webapp access

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   EduHelper Local Dev${NC}"
echo -e "${BLUE}========================================${NC}"

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    [ ! -z "$FASTAPI_PID" ] && kill $FASTAPI_PID 2>/dev/null || true
    [ ! -z "$BOT_PID" ] && kill $BOT_PID 2>/dev/null || true
    [ ! -z "$WEBAPP_PID" ] && kill $WEBAPP_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

mkdir -p "$PROJECT_ROOT/logs"

# Start FastAPI
echo -e "\n${YELLOW}Starting FastAPI...${NC}"
python3 -m admin.backend.main > logs/fastapi.log 2>&1 &
FASTAPI_PID=$!
sleep 2

if kill -0 $FASTAPI_PID 2>/dev/null; then
    echo -e "${GREEN}FastAPI: http://localhost:8000${NC}"
else
    echo -e "${RED}FastAPI failed! Check logs/fastapi.log${NC}"
    exit 1
fi

# Start webapp dev server (optional)
if [ -d "$PROJECT_ROOT/webapp/node_modules" ]; then
    read -p "Start webapp dev server (hot reload)? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Starting webapp dev server...${NC}"
        cd "$PROJECT_ROOT/webapp" && npm run dev > ../logs/webapp.log 2>&1 &
        WEBAPP_PID=$!
        cd "$PROJECT_ROOT"
        sleep 3
        echo -e "${GREEN}Webapp: http://localhost:5174${NC}"
    fi
fi

# Start bot
read -p "Start Telegram bot? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Starting bot...${NC}"
    python3 -m bot.main > logs/bot.log 2>&1 &
    BOT_PID=$!
    sleep 2
    if kill -0 $BOT_PID 2>/dev/null; then
        echo -e "${GREEN}Bot started${NC}"
    else
        echo -e "${RED}Bot failed! Check logs/bot.log${NC}"
    fi
fi

echo -e "\n${GREEN}Ready! Press Ctrl+C to stop${NC}\n"
tail -f logs/*.log 2>/dev/null
