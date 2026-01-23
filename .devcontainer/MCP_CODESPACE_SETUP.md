# MCP Server Configuration Guide for GitHub Codespace

**Last Updated**: 2026-01-23  
**Standard Compliance**: MCP 0.1.0+  
**Environment**: GitHub Codespaces with Python 3.12

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Configuration Files](#configuration-files)
3. [Setup Instructions](#setup-instructions)
4. [Integration Methods](#integration-methods)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)

---

## Overview

### What is MCP?

**Model Context Protocol (MCP)** is a standardized way to connect AI assistants (Claude, Copilot, etc.) to custom tools and data sources via a stdio-based communication protocol.

### Why MCP in Codespace?

- ✅ **Stdio-based** - No Docker required
- ✅ **Secure** - Environment variable isolation
- ✅ **Extensible** - Add custom tools easily
- ✅ **Standard** - Works with Claude, Cline, Copilot

### Architecture

```
┌─────────────────────────────────────────────────────┐
│  AI Assistant (Claude / Copilot / Cline)            │
│                                                     │
├─────────────────────────────────────────────────────┤
│  MCP Protocol Layer (stdio based)                   │
│                                                     │
├─────────────────────────────────────────────────────┤
│  Custom MCP Servers                                 │
│  ├─ AzDO Business Requirements Server               │
│  ├─ Filesystem Server                               │
│  └─ [Future] Additional Servers                     │
│                                                     │
├─────────────────────────────────────────────────────┤
│  Integration Layer                                  │
│  ├─ Azure DevOps API                                │
│  ├─ Codebase Analysis                               │
│  └─ LLM Processing (GROQ/Google)                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Configuration Files

### 1. `cline_mcp_config.json` (for Cline/VS Code)

```json
{
  "mcpServers": {
    "azdo-business-requirements": {
      "command": "python3",
      "args": [
        "/workspaces/Discharge-Summary-Generator/mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "AZDO_ORG_URL": "${AZDO_ORG_URL}",
        "AZDO_PAT_TOKEN": "${AZDO_PAT_TOKEN}",
        "AZDO_PROJECT_NAME": "${AZDO_PROJECT_NAME}",
        "GROQ_API_KEY": "${GROQ_API_KEY}"
      },
      "alwaysAllow": [
        "fetch_work_items",
        "analyze_codebase",
        "generate_business_requirements",
        "validate_credentials"
      ]
    }
  }
}
```

**Key Fields**:
- `command`: Python interpreter (must be in PATH)
- `args`: Path to MCP server script
- `env`: Environment variables passed to server
- `alwaysAllow`: Tools that don't require permission

### 2. `claude_desktop_config.json` (for Claude Desktop)

```json
{
  "mcpServers": {
    "azdo-business-requirements": {
      "command": "python3",
      "args": [
        "/workspaces/Discharge-Summary-Generator/mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "AZDO_ORG_URL": "${AZDO_ORG_URL}",
        "AZDO_PAT_TOKEN": "${AZDO_PAT_TOKEN}",
        "AZDO_PROJECT_NAME": "${AZDO_PROJECT_NAME}",
        "GROQ_API_KEY": "${GROQ_API_KEY}"
      }
    }
  }
}
```

### 3. `.devcontainer/devcontainer.json` (Codespace Container Config)

```json
{
  "customizations": {
    "vscode": {
      "settings": {
        "cline.mcp.servers": {
          "azdo-business-requirements": {
            "command": "python3",
            "args": ["${containerWorkspaceFolder}/mcp_server.py"],
            "env": {
              "PYTHONUNBUFFERED": "1",
              "AZDO_ORG_URL": "${localEnv:AZDO_ORG_URL}",
              "AZDO_PAT_TOKEN": "${localEnv:AZDO_PAT_TOKEN}",
              "AZDO_PROJECT_NAME": "${localEnv:AZDO_PROJECT_NAME}"
            }
          }
        }
      }
    }
  },
  "forwardPorts": [8000, 8001],
  "postCreateCommand": "bash .devcontainer/postCreateCommand.sh"
}
```

---

## Setup Instructions

### Step 1: Verify Dependencies

```bash
python3 --version  # Should be 3.10+
pip3 install mcp pydantic
```

### Step 2: Set Environment Variables

**Option A: Using .env file**

```bash
cp .env.example .env
# Edit .env with your Azure DevOps credentials
export $(cat .env | xargs)
```

**Option B: Using Codespace Secrets**

1. Go to Codespace settings
2. Settings → Secrets and variables → Codespaces
3. Add secrets:
   - `AZDO_ORG_URL`
   - `AZDO_PAT_TOKEN`
   - `AZDO_PROJECT_NAME`
   - `GROQ_API_KEY` (optional)

**Option C: Direct Environment Variables**

```bash
export AZDO_ORG_URL="https://dev.azure.com/your-org"
export AZDO_PAT_TOKEN="your-pat-token"
export AZDO_PROJECT_NAME="YourProject"
export GROQ_API_KEY="your-groq-key"  # optional
```

### Step 3: Run Setup Script

```bash
bash .devcontainer/setup-mcp.sh
```

This script will:
- ✅ Verify Python installation
- ✅ Validate MCP server syntax
- ✅ Copy configuration files
- ✅ Test credentials
- ✅ Display integration instructions

### Step 4: Verify MCP Server

```bash
# Test if server starts
python3 /workspaces/Discharge-Summary-Generator/mcp_server.py

# Expected output: Server listening on stdio
# Press Ctrl+C to stop
```

---

## Integration Methods

### Method 1: Cline in VS Code (Recommended for Codespace)

**Within Codespace:**

1. Install Cline extension (if not already installed)
2. Open Command Palette: `Ctrl+Shift+P`
3. Search: "Preferences: Open Settings (JSON)"
4. Add this to your workspace settings:

```json
{
  "cline.mcp.servers": {
    "azdo": {
      "command": "python3",
      "args": [
        "${workspaceFolder}/mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "AZDO_ORG_URL": "${AZDO_ORG_URL}",
        "AZDO_PAT_TOKEN": "${AZDO_PAT_TOKEN}",
        "AZDO_PROJECT_NAME": "${AZDO_PROJECT_NAME}"
      }
    }
  }
}
```

5. Reload VS Code
6. Open Cline chat
7. Use tools like: "Fetch work items from Azure DevOps project X"

### Method 2: Claude Desktop (Local Machine)

**On your local machine:**

1. Find Claude Desktop config:
   - **macOS**: `~/.claude_desktop_config.json`
   - **Linux**: `~/.claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add server configuration:

```json
{
  "mcpServers": {
    "codespace-azdo": {
      "command": "ssh",
      "args": [
        "codespace@gh.codespaces.net",
        "python3",
        "/workspaces/Discharge-Summary-Generator/mcp_server.py"
      ],
      "env": {
        "AZDO_ORG_URL": "https://dev.azure.com/your-org",
        "AZDO_PAT_TOKEN": "your-token",
        "AZDO_PROJECT_NAME": "Project"
      }
    }
  }
}
```

3. Restart Claude Desktop
4. Check Claude's settings for connected MCP servers

### Method 3: Direct Python Usage

```python
import sys
from mcp_server import AzDOBusinessRequirementsServer

# Create server instance
server = AzDOBusinessRequirementsServer()

# Start server (requires MCP client to connect)
import asyncio
asyncio.run(server.run())
```

### Method 4: FastAPI REST Endpoints

```bash
# Start FastAPI server
python3 API.py

# Use REST endpoints
curl -X POST http://localhost:8000/fetch-work-items \
  -H "Content-Type: application/json" \
  -d '{
    "org_url": "https://dev.azure.com/org",
    "pat_token": "token",
    "project_name": "Project"
  }'
```

---

## MCP Server Specification

### Available Tools

#### 1. `fetch_work_items`

Retrieve work items from Azure DevOps project.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "org_url": {
      "type": "string",
      "description": "Azure DevOps organization URL"
    },
    "pat_token": {
      "type": "string",
      "description": "Personal Access Token"
    },
    "project_name": {
      "type": "string",
      "description": "Project name"
    },
    "team_name": {
      "type": "string",
      "description": "Optional team filter"
    },
    "top": {
      "type": "integer",
      "description": "Max items (default: 100)"
    }
  },
  "required": ["org_url", "pat_token", "project_name"]
}
```

**Example Call**:
```
Tool: fetch_work_items
org_url: https://dev.azure.com/myorg
pat_token: ***
project_name: MyProject
top: 50
```

#### 2. `analyze_codebase`

Scan and analyze Python codebase structure.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "codebase_dir": {
      "type": "string",
      "description": "Root directory (default: current)"
    }
  }
}
```

#### 3. `generate_business_requirements`

Full workflow: fetch items → analyze code → generate summary.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "org_url": { "type": "string" },
    "pat_token": { "type": "string" },
    "project_name": { "type": "string" },
    "use_llm": { "type": "boolean", "default": true },
    "output_dir": { "type": "string" }
  },
  "required": ["org_url", "pat_token", "project_name"]
}
```

#### 4. `validate_credentials`

Test Azure DevOps connectivity.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "org_url": { "type": "string" },
    "pat_token": { "type": "string" }
  },
  "required": ["org_url", "pat_token"]
}
```

---

## Troubleshooting

### Problem: "Docker not found" Error

**Cause**: GitHub's default MCP server tries to use Docker.

**Solution**: Use custom MCP server instead:
```bash
# Use our Python-based server
python3 /workspaces/Discharge-Summary-Generator/mcp_server.py
```

### Problem: "Module not found" Error

**Cause**: MCP SDK not installed.

**Solution**:
```bash
pip install mcp pydantic
```

### Problem: "Connection refused" when calling tools

**Cause**: MCP server not running or misconfigured.

**Solution**:
1. Test server: `python3 mcp_server.py`
2. Check config file syntax: `cat cline_mcp_config.json | jq`
3. Verify environment variables are set
4. Check file permissions: `ls -la mcp_server.py`

### Problem: Environment variables not being passed

**Cause**: Variables not set in current shell.

**Solution**:
```bash
# Load from .env
set -a
source .env
set +a

# Or use export
export AZDO_ORG_URL="..."
export AZDO_PAT_TOKEN="..."
```

### Problem: "Command not found: python3"

**Cause**: Python not in PATH.

**Solution**:
```bash
# Find Python
which python3
# Or use full path
/usr/bin/python3 /workspaces/.../mcp_server.py
```

### Problem: Cline can't see MCP server

**Cause**: Configuration not loaded or server failed to start.

**Solution**:
1. Reload VS Code: `Cmd+Shift+P` → "Developer: Reload Window"
2. Check Cline output for errors
3. Verify server runs manually
4. Check MCP config file path is absolute

---

## Best Practices

### 1. Security

```bash
# ❌ DO NOT commit credentials
git add .env    # WRONG!

# ✅ DO use .env.example template
cp .env.example .env
# Edit .env locally (in .gitignore)

# ✅ DO use Codespace Secrets
# Settings → Secrets and variables → Codespaces
```

### 2. Environment Variables

```bash
# ✅ Separate for each environment
export AZDO_ORG_URL_DEV="..."
export AZDO_ORG_URL_PROD="..."

# ✅ Use descriptive names
export AZDO_PAT_TOKEN  # Clear what it is
# ❌ export TOKEN     # Too generic
```

### 3. Configuration

```json
// ✅ Use absolute paths in config
"args": ["/workspaces/Discharge-Summary-Generator/mcp_server.py"]

// ❌ Don't use relative paths
"args": ["./mcp_server.py"]
```

### 4. Testing

```bash
# ✅ Test MCP server independently
python3 mcp_server.py < /dev/null

# ✅ Test with sample input
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  python3 mcp_server.py

# ✅ Test credentials before connecting
python3 -c "from AzDOAgent import ...; validate_credentials(org, pat)"
```

### 5. Logging

```python
# ✅ Enable logging for debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# ✅ Log important operations
logger.info("Fetching work items...")
logger.error("Failed: %s", str(error))
```

### 6. Error Handling

```python
# ✅ Graceful degradation
try:
    use_llm_enhancement()
except Exception as e:
    logger.warning("LLM unavailable: %s, using fallback", e)
    use_manual_summary()

# ❌ Don't suppress all errors
try:
    something()
except:
    pass
```

---

## Quick Reference

### Start MCP Server
```bash
python3 /workspaces/Discharge-Summary-Generator/mcp_server.py
```

### Setup Configuration
```bash
bash .devcontainer/setup-mcp.sh
```

### Test Credentials
```bash
export AZDO_ORG_URL="..."
export AZDO_PAT_TOKEN="..."
python3 -c "from mcp_server import AzDOBusinessRequirementsServer; s = AzDOBusinessRequirementsServer()"
```

### View Configuration
```bash
cat cline_mcp_config.json | jq
cat claude_desktop_config.json | jq
```

### Check Environment
```bash
printenv | grep AZDO
printenv | grep GROQ
```

---

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Cline Documentation](https://github.com/cline/cline)
- [Azure DevOps API](https://learn.microsoft.com/en-us/rest/api/azure/devops/)
- [Claude Desktop Setup](https://support.anthropic.com/en/articles/8784992)

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-23  
**Maintained By**: Discharge Summary Generator Team
