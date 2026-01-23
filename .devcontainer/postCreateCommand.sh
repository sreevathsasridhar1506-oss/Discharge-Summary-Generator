#!/bin/bash

# Discharge Summary Generator - Codespace Startup Script
# This script runs after the dev container is created

set -e

echo "================================"
echo "Discharge Summary Generator"
echo "Setting up development environment..."
echo "================================"

# Update pip, setuptools, and wheel
echo "Updating pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt
echo "Installing dependencies..."
if [ -f "requirements.txt.txt" ]; then
    pip install -r requirements.txt.txt
else
    echo "Warning: requirements.txt.txt not found"
fi

echo ""
echo "================================"
echo "✓ Setup Complete!"
echo "================================"
echo ""
echo "Available commands:"
echo ""
echo "1. Start FastAPI Application:"
echo "   bash .devcontainer/start.sh"
echo ""
echo "2. Run Azure DevOps Business Requirements Agent:"
echo "   bash .devcontainer/run-azdo-agent.sh"
echo "   (Requires AZDO_ORG_URL, AZDO_PAT_TOKEN, AZDO_PROJECT_NAME)"
echo ""
echo "3. Start MCP Server (for AI Integration):"
echo "   bash .devcontainer/start-mcp-server.sh"
echo "   (Use with Claude, Copilot, and other MCP clients)"
echo ""
echo "4. Health check Azure DevOps Agent:"
echo "   bash .devcontainer/health-check.sh"
echo ""
echo "For more information, see:"
echo "  - .devcontainer/README.md (Overview)"
echo "  - .devcontainer/CODESPACE_SETUP.md (FastAPI setup)"
echo "  - .devcontainer/AZDO_AGENT_SETUP.md (Azure DevOps Agent)"
echo "  - .devcontainer/MCP_SERVER_SETUP.md (MCP Server)"
echo "  - .devcontainer/AZDO_QUICK_START.md (Quick start guide)"
echo ""
