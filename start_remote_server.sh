#!/bin/bash

# TrustyData MCP Remote Server - Startup Script
# This script starts the remote MCP server for claude.ai custom connectors

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   TrustyData MCP Remote Server - Startup         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Please create it first: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if required packages are installed
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! python -c "import starlette" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo -e "${GREEN}Loading environment variables from .env${NC}"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Using environment variables from shell"
fi

# Check required environment variables
if [ -z "$TRUSTYDATA_API_KEY" ]; then
    echo -e "${RED}Error: TRUSTYDATA_API_KEY not set${NC}"
    echo "Please set it in .env or export it:"
    echo "  export TRUSTYDATA_API_KEY='your_api_key'"
    exit 1
fi

if [ -z "$SERVER_AUTH_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  Warning: SERVER_AUTH_TOKEN not set${NC}"
    echo -e "${YELLOW}⚠️  Server will run WITHOUT authentication${NC}"
    echo -e "${YELLOW}⚠️  This is OK for testing but NOT for production${NC}"
    echo ""
    echo "To generate a secure token:"
    echo "  openssl rand -hex 32"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set defaults
PORT=${PORT:-8500}
HOST=${HOST:-127.0.0.1}

echo ""
echo -e "${GREEN}Starting MCP Remote Server...${NC}"
echo -e "  Protocol: ${GREEN}Streamable HTTP (MCP 2025-06-18)${NC}"
echo -e "  Host: ${GREEN}$HOST${NC}"
echo -e "  Port: ${GREEN}$PORT${NC}"
echo -e "  Endpoint: ${GREEN}http://$HOST:$PORT/mcp${NC}"
echo -e "  Health Check: ${GREEN}http://$HOST:$PORT/health${NC}"
echo ""

if [ "$SERVER_AUTH_TOKEN" ]; then
    echo -e "  Auth: ${GREEN}Enabled${NC}"
    echo -e "  Token: ${GREEN}${SERVER_AUTH_TOKEN:0:8}...${NC}"
else
    echo -e "  Auth: ${RED}DISABLED${NC}"
fi

echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the server
python server_remote.py
