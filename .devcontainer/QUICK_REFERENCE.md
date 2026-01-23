# 🚀 Quick Reference Guide

Fast lookup for all Codespace features and commands.

## ⚡ 30-Second Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Azure DevOps PAT token and org
nano .env

# Verify everything works
bash .devcontainer/health-check.sh
```

## 📋 What You Have

| Feature | File | Purpose |
|---------|------|---------|
| **FastAPI App** | `main.py` | Medical discharge summarizer |
| **Azure DevOps Agent** | `AzDOAgent.py` | Fetch work items, generate requirements |
| **MCP Server** | `mcp_server.py` | AI assistant integration (Claude, Copilot) |
| **Codespace Config** | `.devcontainer/devcontainer.json` | Container setup |

## 🎯 Start Using Immediately

### Option A: Web API (FastAPI)
```bash
bash .devcontainer/start.sh
# Visit: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option B: Command Line (Agent)
```bash
bash .devcontainer/run-azdo-agent.sh
# Creates: BUSINESS_REQUIREMENTS.md
```

### Option C: AI Integration (MCP)
```bash
bash .devcontainer/start-mcp-server.sh
# Use with Claude, Copilot, etc.
```

## 🔧 Core Commands

| Command | Purpose |
|---------|---------|
| `bash .devcontainer/start.sh` | Start FastAPI server (port 8000) |
| `bash .devcontainer/run-azdo-agent.sh` | Generate requirements from AzDO |
| `bash .devcontainer/start-mcp-server.sh` | Start MCP server for AI tools |
| `bash .devcontainer/health-check.sh` | Verify setup & credentials |
| `cp .env.example .env` | Create environment config |
| `pip install -r requirements.txt.txt` | Install dependencies |

## 📚 Documentation Quick Links

### For First-Time Users
👉 **Start here**: [README.md](.devcontainer/README.md)

### For FastAPI Setup
👉 [CODESPACE_SETUP.md](.devcontainer/CODESPACE_SETUP.md)

### For Azure DevOps Agent
👉 **Quick**: [AZDO_QUICK_START.md](.devcontainer/AZDO_QUICK_START.md)
👉 **Detailed**: [AZDO_AGENT_SETUP.md](.devcontainer/AZDO_AGENT_SETUP.md)

### For MCP Server
👉 [MCP_SERVER_SETUP.md](.devcontainer/MCP_SERVER_SETUP.md)

### For Complete Overview
👉 [DOCUMENTATION_INDEX.md](.devcontainer/DOCUMENTATION_INDEX.md)

### For Technical Details
👉 [IMPLEMENTATION_SUMMARY.md](.devcontainer/IMPLEMENTATION_SUMMARY.md)
👉 [MCP_IMPLEMENTATION_SUMMARY.md](.devcontainer/MCP_IMPLEMENTATION_SUMMARY.md)

## 🔐 Credential Setup (Choose One)

### Method 1: Environment Variables (Quick)
```bash
export AZDO_ORG_URL="https://dev.azure.com/myorg"
export AZDO_PAT_TOKEN="your-pat-token"
export AZDO_PROJECT_NAME="MyProject"
export GROQ_API_KEY="groq-key"  # optional
```

### Method 2: .env File (Recommended)
```bash
cp .env.example .env
# Edit with your values
nano .env
```

### Method 3: Codespace Secrets (Best)
1. Go to: Repository Settings → Secrets and variables → Codespaces
2. Add: `AZDO_ORG_URL`, `AZDO_PAT_TOKEN`, `AZDO_PROJECT_NAME`
3. They're automatically available in your Codespace

## 🎯 Common Tasks

### "I want to generate business requirements"
```bash
# 1. Set up credentials (see above)
# 2. Run the agent
bash .devcontainer/run-azdo-agent.sh
# 3. Check the generated file
cat BUSINESS_REQUIREMENTS.md
```

### "I want to use Claude with Azure DevOps"
```bash
# 1. Start MCP server
bash .devcontainer/start-mcp-server.sh

# 2. In Claude Desktop config:
{
  "mcpServers": {
    "azure-devops": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}

# 3. Use tools directly in Claude
```

### "I want to develop the API"
```bash
# 1. Start FastAPI
bash .devcontainer/start.sh

# 2. Visit http://localhost:8000/docs

# 3. Test endpoints in Swagger UI
```

### "I want to verify my setup"
```bash
bash .devcontainer/health-check.sh
# Shows: Python, dependencies, credentials status
```

## 🐛 Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| "ModuleNotFoundError" | `pip install -r requirements.txt.txt` |
| "Credentials not found" | `cp .env.example .env` (then edit) |
| "Azure DevOps connection failed" | Check PAT token scope includes "Work Items Read" |
| "No work items returned" | Verify project name matches exactly in Azure DevOps |
| "Port 8000 in use" | Change port in `start.sh` |
| "MCP server crashes" | Check logs: `python mcp_server.py` (no background) |

## 📊 Architecture at a Glance

```
┌─────────────────────────────┐
│  Your Development Options   │
├─────────────────────────────┤
│  • FastAPI (REST API)       │
│  • CLI (run-azdo-agent.sh)  │
│  • MCP (Claude, Copilot)    │
└────────┬────────────────────┘
         │
      ┌──▼──────────────────┐
      │  AzDOAgent          │
      │  (Core Logic)       │
      └──┬─────────────────┬┘
         │                 │
    ┌────▼───┐       ┌────▼────┐
    │ Azure   │       │Codebase │
    │ DevOps  │       │Analysis │
    └─────────┘       └─────────┘
```

## 🎓 Learning Path

1. ✅ **Day 1**: Read [README.md](.devcontainer/README.md)
2. ✅ **Day 1**: Run `bash .devcontainer/health-check.sh`
3. ✅ **Day 2**: Follow [AZDO_QUICK_START.md](.devcontainer/AZDO_QUICK_START.md)
4. ✅ **Day 2**: Generate your first requirements
5. ✅ **Day 3**: Explore [MCP_SERVER_SETUP.md](.devcontainer/MCP_SERVER_SETUP.md)
6. ✅ **Day 3**: Integrate with Claude
7. ✅ **Day 4+**: Customize and extend

## 🔗 Quick Links

### Azure DevOps
- [Get PAT Token](https://dev.azure.com/_usersSettings/tokens)
- [REST API Docs](https://learn.microsoft.com/en-us/azure/devops/integrate/)

### Development Tools
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Codespaces Guide](https://docs.github.com/en/codespaces)
- [MCP Specification](https://modelcontextprotocol.io/)

### Python
- [Pydantic Docs](https://docs.pydantic.dev/)
- [LangChain Docs](https://python.langchain.com/)
- [GROQ API](https://console.groq.com/)

## 💾 Project Files

```
Discharge-Summary-Generator/
├── mcp_server.py              ← MCP server (new)
├── AzDOAgent.py               ← Azure DevOps agent (new)
├── main.py                    ← FastAPI app
├── requirements.txt.txt       ← Dependencies
├── .env.example               ← Configuration template (new)
├── .gitignore                 ← Git rules (new)
│
└── .devcontainer/
    ├── devcontainer.json      ← Codespace config
    ├── postCreateCommand.sh    ← Auto-startup script
    ├── start.sh               ← Start FastAPI
    ├── run-azdo-agent.sh      ← Run agent
    ├── start-mcp-server.sh    ← Start MCP server (new)
    ├── health-check.sh        ← Verify setup
    │
    ├── README.md              ← Overview
    ├── CODESPACE_SETUP.md     ← FastAPI guide
    ├── AZDO_AGENT_SETUP.md    ← Agent guide
    ├── AZDO_QUICK_START.md    ← Quick start
    ├── MCP_SERVER_SETUP.md    ← MCP guide (new)
    ├── IMPLEMENTATION_SUMMARY.md
    ├── MCP_IMPLEMENTATION_SUMMARY.md (new)
    └── DOCUMENTATION_INDEX.md
```

## 🎯 Next Steps

```
1. Create Codespace from this repo
   └─ Auto-setup runs (~2 min)

2. Configure credentials
   └─ cp .env.example .env && nano .env

3. Verify setup
   └─ bash .devcontainer/health-check.sh

4. Choose your path:

   🌐 Web API?        → bash .devcontainer/start.sh
   
   📄 Documents?      → bash .devcontainer/run-azdo-agent.sh
   
   🤖 AI Integration? → bash .devcontainer/start-mcp-server.sh
```

## 🆘 Can't Find Something?

| Looking for... | Check here |
|---|---|
| General info | [README.md](.devcontainer/README.md) |
| FastAPI | [CODESPACE_SETUP.md](.devcontainer/CODESPACE_SETUP.md) |
| Azure DevOps | [AZDO_AGENT_SETUP.md](.devcontainer/AZDO_AGENT_SETUP.md) |
| MCP Server | [MCP_SERVER_SETUP.md](.devcontainer/MCP_SERVER_SETUP.md) |
| Quick answers | [AZDO_QUICK_START.md](.devcontainer/AZDO_QUICK_START.md) |
| All docs | [DOCUMENTATION_INDEX.md](.devcontainer/DOCUMENTATION_INDEX.md) |
| Technical deep-dive | [IMPLEMENTATION_SUMMARY.md](.devcontainer/IMPLEMENTATION_SUMMARY.md) |

## 📞 Support Commands

```bash
# Check if everything is working
bash .devcontainer/health-check.sh

# Verify Python is installed
python3 --version

# Check dependencies
pip list | grep -E "fastapi|azure|mcp"

# See server logs
python mcp_server.py  # Runs in foreground with logs

# Test Azure DevOps connection
python AzDOAgent.py --help
```

---

## 🎉 You're All Set!

Everything is configured and ready to go. Pick an option above and start using:

- 🌐 **FastAPI** - RESTful medical discharge summaries
- 📄 **Agent** - Generate business requirements from Azure DevOps
- 🤖 **MCP** - Use with Claude and other AI assistants

**Questions?** Check the relevant documentation above.

**Happy coding!** 🚀
