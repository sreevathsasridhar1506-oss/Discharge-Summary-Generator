# Discharge Summary Generator - Codespace Setup & Azure DevOps Integration

Complete GitHub Codespace setup with Azure DevOps business requirements agent for the Discharge Summary Generator project.

## 🚀 Quick Start

### In GitHub Codespaces

1. **Create a Codespace** from this repository
2. **Wait for automatic setup** (dependencies auto-installed)
3. **Set environment variables** (if using Azure DevOps):
   ```bash
   export AZDO_ORG_URL="https://dev.azure.com/your-org"
   export AZDO_PAT_TOKEN="your-pat-token"
   export AZDO_PROJECT_NAME="your-project"
   export GROQ_API_KEY="your-groq-key"  # optional
   ```
4. **Choose your action:**
   - Start FastAPI: `bash .devcontainer/start.sh`
   - Generate requirements: `bash .devcontainer/run-azdo-agent.sh`

## 📁 Project Structure

```
Discharge-Summary-Generator/
├── .devcontainer/                    # GitHub Codespace configuration
│   ├── devcontainer.json            # Codespace container definition
│   ├── postCreateCommand.sh          # Runs on Codespace creation
│   ├── start.sh                      # Start FastAPI application
│   ├── run-azdo-agent.sh             # Run Azure DevOps agent
│   ├── health-check.sh               # Verify agent setup
│   ├── CODESPACE_SETUP.md            # FastAPI setup guide
│   ├── AZDO_AGENT_SETUP.md           # Agent configuration guide
│   └── AZDO_QUICK_START.md           # Quick start for agent
│
├── .env.example                      # Example environment variables
├── .gitignore                        # Git ignore file (protects .env)
├── AzDOAgent.py                      # Azure DevOps agent (NEW)
├── main.py                           # FastAPI application
├── requirements.txt.txt              # Python dependencies
│
└── [Other Python modules...]
```

## 🎯 Features

### 1. **GitHub Codespace Integration**
- ✅ Automatic Python 3.12 environment setup
- ✅ Auto-installation of all dependencies
- ✅ VS Code extensions pre-configured
- ✅ Port 8000 auto-forwarded for FastAPI

### 2. **FastAPI Application**
- ✅ Medical discharge summary generation
- ✅ Automatic startup script
- ✅ Swagger/OpenAPI docs at `/docs`
- ✅ Hot-reload development mode

### 3. **Azure DevOps Business Requirements Agent** (NEW)
- ✅ Connects to Azure DevOps projects
- ✅ Retrieves work items (Features, Bugs, User Stories, etc.)
- ✅ Analyzes codebase structure
- ✅ Generates professional markdown requirements document
- ✅ LLM-powered summaries with GROQ
- ✅ Can be scheduled in CI/CD pipelines

### 4. **MCP Server Integration** (NEW)
- ✅ Model Context Protocol (MCP) server for AI assistants
- ✅ Use with Claude, Copilot, and other MCP clients
- ✅ Expose Azure DevOps tools to AI systems
- ✅ Seamless tool calling and integration

## 📚 Documentation

### For FastAPI Setup
👉 [CODESPACE_SETUP.md](.devcontainer/CODESPACE_SETUP.md)

### For Azure DevOps Agent
- **Full Setup Guide**: [AZDO_AGENT_SETUP.md](.devcontainer/AZDO_AGENT_SETUP.md)
- **Quick Start**: [AZDO_QUICK_START.md](.devcontainer/AZDO_QUICK_START.md)

## 🔧 Common Commands

### Start FastAPI Server
```bash
bash .devcontainer/start.sh
# Access at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Generate Business Requirements
```bash
bash .devcontainer/run-azdo-agent.sh
# Generates: BUSINESS_REQUIREMENTS.md
```

### Start MCP Server (for AI Integration)
```bash
bash .devcontainer/start-mcp-server.sh
# Exposes tools to Claude, Copilot, and other MCP clients
```

### Check Agent Configuration
```bash
bash .devcontainer/health-check.sh
# Verifies all dependencies and credentials
```

### Install Dependencies Manually
```bash
pip install -r requirements.txt.txt
```

### Run Python Directly
```bash
python AzDOAgent.py --help
python AzDOAgent.py --output "docs/requirements.md"
python mcp_server.py  # Start MCP server
```

## 🔐 Environment Configuration

### Option 1: Copy from Template
```bash
cp .env.example .env
# Edit .env with your values
```

### Option 2: Set Environment Variables
```bash
export AZDO_ORG_URL="https://dev.azure.com/your-org"
export AZDO_PAT_TOKEN="your-token"
export AZDO_PROJECT_NAME="your-project"
export GROQ_API_KEY="your-groq-key"  # optional
```

### Option 3: Use Codespace Secrets (Recommended)
1. Go to repository Settings → Secrets and variables → Codespaces
2. Add secrets: `AZDO_ORG_URL`, `AZDO_PAT_TOKEN`, `AZDO_PROJECT_NAME`
3. They're automatically available in Codespace

## 🤖 Azure DevOps Agent Usage

### Basic Usage
```bash
# With environment variables set
bash .devcontainer/run-azdo-agent.sh

# Generates BUSINESS_REQUIREMENTS.md
```

### Advanced Usage
```python
from AzDOAgent import AzDOBusinessRequirementsAgent

agent = AzDOBusinessRequirementsAgent(
    organization_url="https://dev.azure.com/my-org",
    pat_token="my-token",
    project_name="MyProject",
    groq_api_key="my-groq-key"
)

# Fetch work items
work_items = agent.fetch_work_items()

# Analyze codebase
analysis = agent.analyze_codebase(".")

# Generate requirements
summary = agent.generate_requirements_summary(work_items, analysis)

# Save to file
path = agent.save_summary_to_file(summary, "REQUIREMENTS.md")
```

## 📊 Generated Output Example

The agent generates a professional markdown file:

```markdown
# Business Requirements Summary

*Generated: 2026-01-23 14:30:00*

## Executive Summary
This project comprises 15 Python modules...

## Azure DevOps Work Items

### Features (3)
- Feature Title (ID: 123, State: Active)

## Technical Architecture

### Modules
- main.py - FastAPI application
- AzDOAgent.py - Business requirements agent

### Data Models
- ConsultationData
- DischargeData
- Medication

## Technology Stack
- fastapi - Web framework
- langchain - LLM orchestration
- azure-devops - AzDO API
...
```

## 🛠️ Technologies Used

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI + Uvicorn | REST API server |
| **LLM Orchestration** | LangChain + LangGraph | AI workflow |
| **LLM Provider** | GROQ | Fast inference |
| **Azure Integration** | Azure DevOps SDK | Work item retrieval |
| **Environment** | Python 3.12 | Runtime |
| **Container** | Codespaces | Development |

## 📋 Requirements File

Python dependencies are automatically installed. Key packages:

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **langchain** - LLM orchestration
- **azure-devops** - Azure DevOps API
- **azure-identity** - Azure authentication
- **langchain-groq** - GROQ LLM integration
- **pydantic** - Data validation

See `requirements.txt.txt` for complete list.

## 🔍 Troubleshooting

### "Credentials not configured"
```bash
cp .env.example .env
# Edit .env with your Azure DevOps details
```

### "No module named 'azure.devops'"
```bash
pip install -r requirements.txt.txt
```

### "Cannot connect to Azure DevOps"
- Verify PAT token is valid
- Check project name matches exactly
- Ensure token has "Work Items (Read)" scope
- Verify organization URL format: `https://dev.azure.com/org-name`

### "LLM features not working"
- GROQ_API_KEY is optional
- Agent works without it (generates manual summaries)
- Get key from https://console.groq.com/keys

See [AZDO_AGENT_SETUP.md](.devcontainer/AZDO_AGENT_SETUP.md#troubleshooting) for more troubleshooting.

## 🔄 Integration with CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Setup dependencies
  run: pip install -r requirements.txt.txt

- name: Generate Business Requirements
  env:
    AZDO_ORG_URL: ${{ secrets.AZDO_ORG_URL }}
    AZDO_PAT_TOKEN: ${{ secrets.AZDO_PAT_TOKEN }}
    AZDO_PROJECT_NAME: ${{ secrets.AZDO_PROJECT_NAME }}
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
  run: python AzDOAgent.py --output "docs/REQUIREMENTS.md"

- name: Commit and push
  run: |
    git add docs/REQUIREMENTS.md
    git commit -m "Updated business requirements" || true
    git push
```

## 📱 Port Forwarding

Port 8000 is automatically forwarded in Codespace:
- **FastAPI Server**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎓 Learning Resources

- [GitHub Codespaces Documentation](https://docs.github.com/en/codespaces)
- [Azure DevOps REST API](https://learn.microsoft.com/en-us/azure/devops/integrate/concepts/rest-api-overview)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [GROQ API Documentation](https://console.groq.com/docs)

## 🤝 Contributing

To improve this setup:

1. Test changes in a Codespace
2. Update relevant documentation files
3. Test agent with sample Azure DevOps projects
4. Ensure health-check passes

## 📝 License

This project inherits the license of the main Discharge-Summary-Generator project.

## 📞 Support

For issues:

1. Run health check: `bash .devcontainer/health-check.sh`
2. Check appropriate documentation:
   - FastAPI: [CODESPACE_SETUP.md](.devcontainer/CODESPACE_SETUP.md)
   - Agent: [AZDO_AGENT_SETUP.md](.devcontainer/AZDO_AGENT_SETUP.md)
3. Verify environment variables are set correctly
4. Check that dependencies are installed: `pip list | grep azure-devops`

---

**Ready to start?** Create a Codespace and run: `bash .devcontainer/run-azdo-agent.sh`

✨ **Happy coding!**
