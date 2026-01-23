#!/bin/bash

# Azure DevOps Business Requirements MCP Server Startup
# Runs the MCP server for Copilot and other MCP clients

set -e

echo "=========================================="
echo "Azure DevOps Agent - MCP Server"
echo "=========================================="
echo ""

# Check if dependencies are installed
if ! python3 -c "import mcp" 2>/dev/null; then
    echo "Installing MCP SDK..."
    pip install mcp>=0.1.0
fi

echo "Starting MCP Server..."
echo ""
echo "This server provides tools for:"
echo "  • Fetching Azure DevOps work items"
echo "  • Analyzing codebase structure"
echo "  • Generating business requirements"
echo ""
echo "Use Ctrl+C to stop the server"
echo ""

# Run the MCP server
python mcp_server.py
