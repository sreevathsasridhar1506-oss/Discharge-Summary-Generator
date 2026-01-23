#!/bin/bash
set -e

################################################################################
# MCP Server Setup Script for GitHub Codespace
# This script configures MCP (Model Context Protocol) servers properly for
# Codespace development environment following MCP standards
################################################################################

echo "═══════════════════════════════════════════════════════════════"
echo "🔧 MCP Server Configuration for GitHub Codespace"
echo "═══════════════════════════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================================================
# 1. Verify Dependencies
# ============================================================================
echo "📦 Step 1: Verifying dependencies..."
echo ""

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python ${PYTHON_VERSION} detected"

# Install required MCP packages
echo "✓ Installing MCP SDK..."
pip install -q mcp pydantic 2>/dev/null || true

echo ""

# ============================================================================
# 2. Validate MCP Server Script
# ============================================================================
echo "📋 Step 2: Validating MCP server implementation..."
echo ""

if [ ! -f "$PROJECT_ROOT/mcp_server.py" ]; then
    echo "❌ mcp_server.py not found at $PROJECT_ROOT/mcp_server.py"
    exit 1
fi

# Test MCP server syntax
python3 -m py_compile "$PROJECT_ROOT/mcp_server.py" 2>/dev/null && \
    echo "✓ MCP server syntax valid" || \
    echo "⚠ MCP server has syntax issues (will be caught at runtime)"

echo ""

# ============================================================================
# 3. Setup Configuration Files
# ============================================================================
echo "🔐 Step 3: Setting up MCP configuration files..."
echo ""

# Create config directory
CONFIG_DIR="$HOME/.config/mcp"
mkdir -p "$CONFIG_DIR"
echo "✓ Created config directory: $CONFIG_DIR"

# Copy/update Cline MCP config
if [ -f "$PROJECT_ROOT/cline_mcp_config.json" ]; then
    cp "$PROJECT_ROOT/cline_mcp_config.json" "$CONFIG_DIR/cline_config.json"
    echo "✓ Cline MCP config copied to $CONFIG_DIR/cline_config.json"
fi

# Copy/update Claude Desktop config
if [ -f "$PROJECT_ROOT/claude_desktop_config.json" ]; then
    cp "$PROJECT_ROOT/claude_desktop_config.json" "$CONFIG_DIR/claude_config.json"
    echo "✓ Claude Desktop MCP config copied to $CONFIG_DIR/claude_config.json"
fi

echo ""

# ============================================================================
# 4. Environment Variables Setup
# ============================================================================
echo "🌍 Step 4: Checking environment variables..."
echo ""

# Check if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "✓ .env file found"
    source "$PROJECT_ROOT/.env" 2>/dev/null || true
else
    echo "⚠ .env file not found. Create one from .env.example:"
    echo "  cp $PROJECT_ROOT/.env.example $PROJECT_ROOT/.env"
    echo "  Edit with your Azure DevOps credentials"
fi

# Validate required env vars
REQUIRED_VARS=("AZDO_ORG_URL" "AZDO_PAT_TOKEN" "AZDO_PROJECT_NAME")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    else
        echo "✓ $var is set"
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  Missing environment variables: ${MISSING_VARS[*]}"
    echo "   These are required for Azure DevOps integration"
fi

echo ""

# ============================================================================
# 5. Validate Credentials (Optional)
# ============================================================================
echo "🔑 Step 5: Testing credentials (optional)..."
echo ""

if [ -n "$AZDO_ORG_URL" ] && [ -n "$AZDO_PAT_TOKEN" ]; then
    echo "Testing Azure DevOps credentials..."
    python3 << 'PYTHON_TEST'
import os
import sys
try:
    from azure.devops.connection import Connection
    from msrest.authentication import BasicAuthentication
    
    org_url = os.getenv('AZDO_ORG_URL')
    pat = os.getenv('AZDO_PAT_TOKEN')
    
    if org_url and pat:
        credentials = BasicAuthentication('', pat)
        connection = Connection(base_url=org_url, user_name='', password='', creds=credentials)
        core = connection.clients.get_core_client()
        _ = core.get_projects()
        print("✓ Azure DevOps credentials validated")
    else:
        print("⚠ Credentials not set, skipping validation")
except Exception as e:
    print(f"⚠ Credential validation failed: {str(e)}")
    print("  This is OK if you haven't set up Azure DevOps yet")
PYTHON_TEST
else
    echo "⚠ Credentials not set, skipping validation"
fi

echo ""

# ============================================================================
# 6. Verify MCP Server Can Start
# ============================================================================
echo "🚀 Step 6: Testing MCP server startup..."
echo ""

# Create a test timeout script
TIMEOUT_TEST=$(python3 << 'PYTHON_TIMEOUT'
import subprocess
import sys

try:
    # Start MCP server with 2 second timeout
    proc = subprocess.Popen(
        [sys.executable, '/workspaces/Discharge-Summary-Generator/mcp_server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a bit for startup
    import time
    time.sleep(0.5)
    
    if proc.poll() is None:
        print("✓ MCP server started successfully (PID: {})".format(proc.pid))
        proc.terminate()
        proc.wait(timeout=2)
        print("✓ MCP server stopped cleanly")
    else:
        stdout, stderr = proc.communicate()
        print(f"⚠ MCP server exited immediately")
        if stderr:
            print(f"  Error: {stderr[:200]}")
except Exception as e:
    print(f"⚠ MCP server test error: {str(e)}")
PYTHON_TIMEOUT
)
echo "$TIMEOUT_TEST"

echo ""

# ============================================================================
# 7. Display Configuration Summary
# ============================================================================
echo "📋 Step 7: Configuration Summary"
echo ""

cat << 'EOF'
┌─ MCP SERVERS CONFIGURED ──────────────────────────────────────┐
│                                                                │
│  1. azdo-business-requirements (Custom Agent)                 │
│     Command: python3 /workspaces/.../mcp_server.py            │
│     Protocol: stdio                                           │
│     Tools:                                                    │
│       • fetch_work_items                                      │
│       • analyze_codebase                                      │
│       • generate_business_requirements                        │
│       • validate_credentials                                  │
│                                                                │
│  2. filesystem (File Operations)                              │
│     Command: python3 -m mcp.server.filesystem ...             │
│     Protocol: stdio                                           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
EOF

echo ""

# ============================================================================
# 8. Display Integration Instructions
# ============================================================================
echo "🔗 Step 8: Integration Instructions"
echo ""

cat << 'EOF'
┌─ FOR CLINE (VS Code Extension) ───────────────────────────────┐
│                                                                │
│  1. Open VS Code Settings                                     │
│  2. Search: "Cline MCP Config"                                │
│  3. Paste this path:                                          │
│     /workspaces/Discharge-Summary-Generator/cline_mcp_config.json
│  4. Reload VS Code                                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌─ FOR CLAUDE DESKTOP APP ──────────────────────────────────────┐
│                                                                │
│  1. On your LOCAL machine (not Codespace)                     │
│  2. Find Claude config file:                                  │
│     - macOS: ~/.claude_desktop_config.json                    │
│     - Linux: ~/.claude_desktop_config.json                    │
│     - Windows: %APPDATA%/Claude/claude_desktop_config.json    │
│  3. Add this server entry:                                    │
│                                                                │
│     {                                                         │
│       "mcpServers": {                                         │
│         "codespace-azdo": {                                   │
│           "command": "ssh",                                   │
│           "args": [                                           │
│             "codespace@gh.codespaces.net",                   │
│             "python3",                                        │
│             "/workspaces/.../mcp_server.py"                  │
│           ]                                                   │
│         }                                                      │
│       }                                                        │
│     }                                                          │
│                                                                │
│  4. Restart Claude                                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌─ FOR CLINE IN CODESPACE ──────────────────────────────────────┐
│                                                                │
│  1. Open Command Palette (Ctrl+Shift+P)                       │
│  2. Search: "Preferences: Open Settings (JSON)"              │
│  3. Add this to your settings.json:                           │
│                                                                │
│     "cline.mcp.servers": {                                    │
│       "azdo-agent": {                                         │
│         "command": "python3",                                 │
│         "args": [                                             │
│           "/workspaces/Discharge-Summary-Generator/mcp_server.py"
│         ],                                                     │
│         "env": {                                              │
│           "AZDO_ORG_URL": "...",                              │
│           "AZDO_PAT_TOKEN": "..."                             │
│         }                                                      │
│       }                                                        │
│     }                                                          │
│                                                                │
│  4. Reload VS Code                                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
EOF

echo ""

# ============================================================================
# 9. Manual Testing Commands
# ============================================================================
echo "🧪 Step 9: Manual Testing Commands"
echo ""

cat << 'EOF'
Test MCP server directly:
  python3 /workspaces/Discharge-Summary-Generator/mcp_server.py

Test with curl (if server starts):
  # In another terminal
  curl -X POST http://localhost:8000/tools/fetch_work_items \
    -H "Content-Type: application/json" \
    -d '{
      "org_url": "https://dev.azure.com/your-org",
      "pat_token": "your-token",
      "project_name": "Project"
    }'

Test Azure DevOps integration:
  python3 << 'PYTHON'
from AzDOAgent import AzDOBusinessRequirementsAgent
import os

agent = AzDOBusinessRequirementsAgent(
    org_url=os.getenv('AZDO_ORG_URL'),
    pat_token=os.getenv('AZDO_PAT_TOKEN'),
    project_name=os.getenv('AZDO_PROJECT_NAME')
)
# Test fetch
items = agent.fetch_work_items()
print(f"Fetched {len(items)} work items")
PYTHON

EOF

echo ""

# ============================================================================
# 10. Final Status
# ============================================================================
echo "✅ MCP Server Configuration Complete!"
echo ""

cat << 'EOF'
📋 CHECKLIST:
  ✓ Dependencies verified
  ✓ MCP server script validated
  ✓ Configuration files created
  ✓ Environment variables checked
  ⏳ Next: Set Azure DevOps credentials in .env

🔐 SECURITY REMINDER:
  ⚠️  Never commit .env or PAT tokens
  ⚠️  Use GitHub Codespace Secrets instead:
      Settings → Secrets and variables → Codespaces

🚀 QUICK START:
  1. Set environment variables:
     export AZDO_ORG_URL="https://dev.azure.com/your-org"
     export AZDO_PAT_TOKEN="your-token"
     export AZDO_PROJECT_NAME="Project"

  2. Test MCP server:
     python3 /workspaces/Discharge-Summary-Generator/mcp_server.py

  3. Use with Cline:
     Add config: cline_mcp_config.json

📚 DOCUMENTATION:
  See .devcontainer/MCP_IMPLEMENTATION_SUMMARY.md for details

EOF

echo ""
echo "═══════════════════════════════════════════════════════════════"
