#!/bin/bash

# Build Mini App for production

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEBAPP_DIR="$PROJECT_ROOT/webapp"

cd "$WEBAPP_DIR"

echo -e "${YELLOW}Building Mini App...${NC}"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install
fi

# Build
npm run build

echo -e "${GREEN}Build complete!${NC}"
echo -e "Output: $WEBAPP_DIR/dist/"
echo -e ""
echo -e "FastAPI will serve it automatically from /webapp"
