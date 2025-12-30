#!/bin/bash

# Development script with Cloudflare tunnel
# Starts FastAPI backend and creates a public tunnel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   EduHelper Dev Environment${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}cloudflared not found!${NC}"
    echo -e "Install with: ${YELLOW}brew install cloudflared${NC}"
    exit 1
fi

# Check if python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}python3 not found!${NC}"
    exit 1
fi

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"

    # Kill FastAPI
    if [ ! -z "$FASTAPI_PID" ]; then
        kill $FASTAPI_PID 2>/dev/null || true
        echo -e "${GREEN}FastAPI stopped${NC}"
    fi

    # Kill cloudflared
    if [ ! -z "$TUNNEL_PID" ]; then
        kill $TUNNEL_PID 2>/dev/null || true
        echo -e "${GREEN}Tunnel stopped${NC}"
    fi

    # Kill bot if running
    if [ ! -z "$BOT_PID" ]; then
        kill $BOT_PID 2>/dev/null || true
        echo -e "${GREEN}Bot stopped${NC}"
    fi

    exit 0
}

trap cleanup SIGINT SIGTERM

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Start FastAPI backend
echo -e "\n${YELLOW}Starting FastAPI backend...${NC}"
python3 -m admin.backend.main > logs/fastapi.log 2>&1 &
FASTAPI_PID=$!
sleep 2

# Check if FastAPI started
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo -e "${RED}FastAPI failed to start! Check logs/fastapi.log${NC}"
    exit 1
fi
echo -e "${GREEN}FastAPI running on http://localhost:8000 (PID: $FASTAPI_PID)${NC}"

# Start Cloudflare tunnel (using http2 protocol for better compatibility)
echo -e "\n${YELLOW}Starting Cloudflare tunnel...${NC}"
cloudflared tunnel --url http://localhost:8000 --protocol http2 > logs/tunnel.log 2>&1 &
TUNNEL_PID=$!

# Wait for tunnel URL
echo -e "${YELLOW}Waiting for tunnel URL...${NC}"
TUNNEL_URL=""
for i in {1..30}; do
    TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' logs/tunnel.log 2>/dev/null | head -1)
    if [ ! -z "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}Failed to get tunnel URL! Check logs/tunnel.log${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}Tunnel URL: ${TUNNEL_URL}${NC}"

# Update .env file with tunnel URL
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # Backup .env
    cp "$ENV_FILE" "$ENV_FILE.bak"

    # Update or add WEBAPP_URL
    if grep -q "^WEBAPP_URL=" "$ENV_FILE"; then
        sed -i '' "s|^WEBAPP_URL=.*|WEBAPP_URL=${TUNNEL_URL}/webapp|" "$ENV_FILE"
    else
        echo "WEBAPP_URL=${TUNNEL_URL}/webapp" >> "$ENV_FILE"
    fi

    echo -e "${GREEN}Updated .env with WEBAPP_URL${NC}"
fi

# Print summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Development environment ready!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e ""
echo -e "  ${YELLOW}Public URL:${NC}     $TUNNEL_URL"
echo -e "  ${YELLOW}Mini App:${NC}       $TUNNEL_URL/webapp"
echo -e "  ${YELLOW}API:${NC}            $TUNNEL_URL/api"
echo -e "  ${YELLOW}Health:${NC}         $TUNNEL_URL/health"
echo -e ""
echo -e "  ${YELLOW}YooKassa webhook:${NC}"
echo -e "  $TUNNEL_URL/api/webhook/yookassa"
echo -e ""
echo -e "  ${YELLOW}Local:${NC}"
echo -e "  FastAPI:        http://localhost:8000"
echo -e "  Logs:           $PROJECT_ROOT/logs/"
echo -e ""
echo -e "${BLUE}========================================${NC}"
echo -e "Press ${RED}Ctrl+C${NC} to stop all services"
echo -e "${BLUE}========================================${NC}"

# Optional: Start the bot
read -p "Start Telegram bot? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Starting Telegram bot...${NC}"
    python3 -m bot.main > logs/bot.log 2>&1 &
    BOT_PID=$!
    sleep 2

    if kill -0 $BOT_PID 2>/dev/null; then
        echo -e "${GREEN}Bot running (PID: $BOT_PID)${NC}"
    else
        echo -e "${RED}Bot failed to start! Check logs/bot.log${NC}"
    fi
fi

# Keep script running
echo -e "\n${YELLOW}Watching logs... (Ctrl+C to stop)${NC}\n"
tail -f logs/fastapi.log logs/tunnel.log 2>/dev/null
