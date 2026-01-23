# Azure DevOps MCP Server Setup

Complete guide to running the Azure DevOps Business Requirements MCP (Model Context Protocol) server in your Codespace.

## What is MCP?

**Model Context Protocol (MCP)** is a standardized protocol for connecting AI systems with external data sources and tools. It allows:

- 🤖 **Claude and other AI assistants** to use your custom tools
- 🔌 **Seamless integration** with your development environment
- 🎯 **Direct access** to Azure DevOps work items and codebase analysis

Read more: https://modelcontextprotocol.io/

## 🚀 Quick Start

### Start the MCP Server

```bash
bash .devcontainer/start-mcp-server.sh
```

The server will start and listen for incoming requests from MCP clients (like Claude).

### Configure in Claude/Copilot

The server runs on stdio, making it easy to integrate with MCP clients. Configuration depends on your client:

#### For Claude Desktop
Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "azure-devops-agent": {
      "command": "python",
      "args": ["/path/to/Discharge-Summary-Generator/mcp_server.py"]
    }
  }
}
```

#### For GitHub Copilot
Instructions coming soon - check back for Copilot MCP integration details.

## 🛠️ Available Tools

The MCP server exposes 4 tools:

### 1. `fetch_work_items`
**Fetch work items from an Azure DevOps project**

```
Organization URL: https://dev.azure.com/myorg
PAT Token: [your-pat-token]
Project Name: MyProject
Team Name: [optional]
Top: 50 [max items to retrieve]
```

Returns:
- Features, Bugs, User Stories, and other work item types
- Organized by type with counts
- Full metadata (ID, title, state, assignee)

### 2. `analyze_codebase`
**Analyze codebase structure**

```
Codebase Directory: . [current directory]
```

Returns:
- Python modules and files
- Data models and classes
- Main components and functions
- Dependencies from requirements files

### 3. `generate_business_requirements`
**Generate comprehensive business requirements summary**

Combines work items + codebase analysis into a professional markdown document.

```
Organization URL: https://dev.azure.com/myorg
PAT Token: [your-pat-token]
Project Name: MyProject
Codebase Directory: . [default]
Output File: BUSINESS_REQUIREMENTS.md [default]
GROQ API Key: [optional, for LLM summaries]
```

Returns:
- Executive summary
- Work items organized by type
- Technical architecture overview
- Data models and components
- Technology stack
- Success criteria

### 4. `validate_credentials`
**Test Azure DevOps connectivity**

```
Organization URL: https://dev.azure.com/myorg
PAT Token: [your-pat-token]
```

Returns:
- ✓ Connection successful
- ✗ Connection failed with error details

## 🔐 Environment Setup

### Method 1: Environment Variables

```bash
export AZDO_ORG_URL="https://dev.azure.com/your-org"
export AZDO_PAT_TOKEN="your-pat-token"
export AZDO_PROJECT_NAME="your-project"
export GROQ_API_KEY="your-groq-key"  # optional
```

### Method 2: .env File

Create a `.env` file in the project root:

```env
AZDO_ORG_URL=https://dev.azure.com/your-org
AZDO_PAT_TOKEN=your-pat-token
AZDO_PROJECT_NAME=your-project
GROQ_API_KEY=your-groq-key
```

The .env file is Git-ignored for security.

### Method 3: Codespace Secrets (Recommended)

1. Go to repository Settings → Secrets and variables → Codespaces
2. Add secrets:
   - `AZDO_ORG_URL`
   - `AZDO_PAT_TOKEN`
   - `AZDO_PROJECT_NAME`
   - `GROQ_API_KEY` (optional)

They're automatically available in your Codespace.

## 🔍 Getting Your PAT Token

1. Visit https://dev.azure.com
2. Click your profile icon → **Personal access tokens**
3. Click **New Token**
4. Fill in:
   - **Name**: "Codespace MCP Server"
   - **Organization**: Select your organization
   - **Scopes**: Select:
     - ✓ Work Items (Read)
     - ✓ Project & Team (Read)
   - **Expiration**: 90 days (or your preference)
5. Click **Create** and copy the token immediately (you won't see it again!)

## 📋 Running the Server

### Option 1: Direct Execution

```bash
bash .devcontainer/start-mcp-server.sh
```

### Option 2: Manual Python Execution

```bash
python mcp_server.py
```

### Option 3: Using MCP CLI (if installed)

```bash
mcp run python mcp_server.py
```

## 🧪 Testing the Server

### Option 1: Using Inspector Tool

If you have the MCP inspector installed:

```bash
mcp inspect python /path/to/mcp_server.py
```

This shows all available tools and their schemas.

### Option 2: Manual Testing

You can test by sending MCP requests through a compatible client. The server expects:

```json
{
  "method": "tools/call",
  "params": {
    "name": "validate_credentials",
    "arguments": {
      "organization_url": "https://dev.azure.com/myorg",
      "pat_token": "your-token"
    }
  }
}
```

## 🔄 Integration Examples

### Example 1: Generate Requirements in Codespace

```bash
# Terminal 1: Start MCP server
bash .devcontainer/start-mcp-server.sh

# Terminal 2: Use Claude CLI or other MCP client
# Call the generate_business_requirements tool with your Azure DevOps credentials
```

### Example 2: Fetch Specific Work Items

```bash
# In your MCP client, call:
{
  "tool": "fetch_work_items",
  "arguments": {
    "organization_url": "https://dev.azure.com/acme",
    "pat_token": "pats***token***",
    "project_name": "MyProject",
    "top": 25
  }
}
```

### Example 3: Full Workflow

```bash
# Step 1: Validate connection
validate_credentials(org_url, pat_token)
# ✓ Connection successful

# Step 2: Fetch work items
work_items = fetch_work_items(org_url, pat_token, project, top=50)
# Returns: 50 work items organized by type

# Step 3: Analyze codebase
analysis = analyze_codebase(".")
# Returns: modules, models, components, dependencies

# Step 4: Generate requirements
output = generate_business_requirements(org_url, pat_token, project)
# Creates: BUSINESS_REQUIREMENTS.md
```

## 🐳 Running in Codespace with Auto-Start

To have the MCP server auto-start when your Codespace loads, add to `.devcontainer/postCreateCommand.sh`:

```bash
# Start MCP server in background
nohup bash .devcontainer/start-mcp-server.sh > /tmp/mcp-server.log 2>&1 &
echo "MCP Server started in background"
```

**Note:** Only do this if you have credentials configured via environment variables or Codespace secrets.

## 🛠️ Architecture

```
┌─────────────────────────────────────┐
│  MCP Client                         │
│  (Claude, Copilot, etc.)            │
└─────────────┬───────────────────────┘
              │
        stdio protocol
              │
┌─────────────▼───────────────────────┐
│  MCP Server (mcp_server.py)         │
│  ├─ Tool: fetch_work_items          │
│  ├─ Tool: analyze_codebase          │
│  ├─ Tool: generate_requirements     │
│  └─ Tool: validate_credentials      │
└─────────────┬───────────────────────┘
              │
              ├──────────────────────────┐
              │                          │
        ┌─────▼──────┐        ┌────────▼────┐
        │  AzDO      │        │ AzDOAgent   │
        │  Client    │        │ (Analysis)  │
        └─────┬──────┘        └────────┬────┘
              │                        │
        ┌─────▼──────────────────────▼────┐
        │  Azure DevOps                    │
        │  Work Items / Projects           │
        └──────────────────────────────────┘
```

## 📊 MCP Server Output

When tools are called, the server returns structured text responses:

```
✓ Successfully fetched 25 work items from 'MyProject'

Work Items Breakdown:
============================================================

Features (3):
----------------------------------------
  [1] Implement real-time sync
      ID: 123 | State: Active
      Assigned to: John Doe
  
  [2] Add user authentication
      ID: 124 | State: In Progress

... and 1 more feature
```

## 🔧 Advanced Configuration

### Custom Tool Schemas

The MCP server defines schemas for each tool. You can view them by:

1. Running the server
2. Checking logs for tool definitions
3. Using MCP inspector: `mcp inspect python mcp_server.py`

### Extending the Server

To add new tools, edit `mcp_server.py`:

```python
@self.server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... existing tools ...
        Tool(
            name="my_new_tool",
            description="Does something cool",
            inputSchema={...},
        ),
    ]

@self.server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "my_new_tool":
        return await self._my_new_tool(**arguments)
```

## 📚 Documentation

- Full setup: [.devcontainer/AZDO_AGENT_SETUP.md](.../AZDO_AGENT_SETUP.md)
- Quick start: [.devcontainer/AZDO_QUICK_START.md](.../AZDO_QUICK_START.md)
- MCP specification: https://modelcontextprotocol.io/
- Azure DevOps API: https://learn.microsoft.com/en-us/azure/devops/integrate/

## 🆘 Troubleshooting

### "ModuleNotFoundError: No module named 'mcp'"

```bash
pip install -r requirements.txt.txt
```

### "Connection refused"

- Ensure Azure DevOps PAT token is valid
- Check organization URL format: `https://dev.azure.com/org-name`
- Verify PAT has "Work Items (Read)" scope

### "No work items returned"

- Verify project name matches exactly in Azure DevOps
- Check that your PAT token has access to the project
- Use `validate_credentials` tool to test connection first

### Server crashes with errors

Check the server logs:

```bash
# If running in background
tail -f /tmp/mcp-server.log

# Or run in foreground to see output
python mcp_server.py
```

## 🔐 Security Best Practices

✅ **Do:**
- Store PAT tokens in Codespace secrets or .env
- Use minimal scopes (Work Items Read, Project & Team Read)
- Rotate tokens regularly
- Use HTTPS for organization URLs

❌ **Don't:**
- Commit .env file to Git
- Share PAT tokens in chat or messages
- Use tokens with unnecessary scopes
- Expose credentials in logs

## 📝 MCP Server Logs

The server logs all operations. Check them for debugging:

```bash
# Running with logs
python mcp_server.py 2>&1 | tee mcp-server.log

# Or tail logs in background
tail -f /tmp/mcp-server.log
```

Log format:
```
2026-01-23 10:30:45 - mcp_server - INFO - Calling tool: fetch_work_items
2026-01-23 10:30:46 - mcp_server - INFO - Fetching work items from https://dev.azure.com/myorg/MyProject
2026-01-23 10:30:47 - mcp_server - INFO - Successfully retrieved 25 work items
```

## 💡 Tips & Tricks

**Tip 1:** Use `validate_credentials` first
Always test your credentials before running other tools:
```
validate_credentials() → ✓ Connected
fetch_work_items() → ✓ Works!
```

**Tip 2:** Cache results in your client
The server may be called multiple times. Consider caching:
- Work items (they don't change frequently)
- Codebase analysis (static unless code changes)

**Tip 3:** Use filters wisely
Instead of fetching all 1000 items, use `top` parameter:
```
fetch_work_items(top=25) # Faster and cleaner
```

**Tip 4:** Chain tool calls
Create complete workflows by chaining tools:
```
validate_credentials()
→ fetch_work_items()
→ analyze_codebase()
→ generate_business_requirements()
```

---

## Next Steps

1. ✅ Set up your environment variables or .env file
2. ✅ Get your Azure DevOps PAT token
3. ✅ Start the MCP server: `bash .devcontainer/start-mcp-server.sh`
4. ✅ Configure your MCP client (Claude, etc.)
5. ✅ Start using the tools!

---

**Questions?** Check [AZDO_AGENT_SETUP.md](AZDO_AGENT_SETUP.md) or [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md).

**Happy MCP coding!** 🚀
