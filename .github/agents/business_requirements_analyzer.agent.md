---
description: 'Azure DevOps Business Requirements Generator - Fetches work items from Azure DevOps projects and generates comprehensive business requirements documentation with codebase analysis.'
tools:
  ['execute', 'github.vscode-pull-request-github/copilotCodingAgent', 'github.vscode-pull-request-github/issue_fetch', 'github.vscode-pull-request-github/doSearch']
---

## Azure DevOps Business Requirements Analyzer

### Purpose
This custom agent connects to Azure DevOps, retrieves work items from specified projects and teams, analyzes your codebase, and generates comprehensive business requirements documentation in markdown format.

### When to Use
- **Generate requirements docs** from Azure DevOps work items
- **Analyze codebase structure** and extract modules/classes automatically
- **Create business requirement summaries** with LLM enhancement
- **Document project scope** based on actual work items and code
- **Integrate with AI assistants** (Claude, Copilot) via MCP server

### Ideal Inputs
```
- Azure DevOps Organization URL (e.g., https://dev.azure.com/myorg)
- Personal Access Token (PAT) with work items read permission
- Project name (e.g., "MyProject")
- [Optional] Team name
- [Optional] Repository root directory for code analysis
```

### Expected Outputs
```
- Business requirements markdown document
- Codebase architecture analysis
- Work item summaries with descriptions
- Risk assessment and dependencies
- Generated files:
  - BUSINESS_REQUIREMENTS.md (main output)
  - requirements_summary.json (structured data)
  - codebase_analysis.json (code structure)
```

### Available MCP Tools

#### 1. fetch_work_items
Retrieves work items from Azure DevOps project
```
Parameters:
  - org_url (required): Azure DevOps organization URL
  - pat_token (required): Personal Access Token
  - project_name (required): Project name
  - team_name (optional): Team name to filter items
  - top (optional): Maximum work items to fetch (default: 100)
```

#### 2. analyze_codebase
Scans and analyzes Python codebase structure
```
Parameters:
  - codebase_dir (optional): Root directory to analyze (default: current dir)
  
Returns:
  - Module list with classes and functions
  - Code metrics and complexity
  - Dependencies and imports
```

#### 3. generate_business_requirements
Full workflow: fetch items → analyze code → generate summary
```
Parameters:
  - org_url (required): Azure DevOps organization URL
  - pat_token (required): Personal Access Token
  - project_name (required): Project name
  - team_name (optional): Team filter
  - codebase_dir (optional): Code analysis directory
  - use_llm (optional): Enable LLM enhancement (default: true)
  - output_dir (optional): Output directory (default: current dir)
  
Triggers custom agent workflow with progress reporting
```

#### 4. validate_credentials
Tests Azure DevOps connectivity and PAT validity
```
Parameters:
  - org_url (required): Azure DevOps organization URL
  - pat_token (required): Personal Access Token

Returns:
  - Connectivity status
  - Token validity
  - Organization details
```

### How the Agent Works

**Workflow**:
1. **Validate** Azure DevOps credentials
2. **Fetch** work items from specified project
3. **Analyze** your codebase structure (AST-based)
4. **Generate** requirements summary (manual or LLM-enhanced)
5. **Save** results to markdown and JSON files
6. **Report** progress and completion status

**Progress Reporting**:
- Real-time status messages via stdio
- Error handling with detailed diagnostics
- Fallback to manual summary if LLM unavailable

### Prerequisites
Before using this agent, ensure:

```bash
# 1. Install dependencies
pip install -r requirements.txt.txt

# 2. Set up environment variables
export AZDO_ORG_URL="https://dev.azure.com/your-org"
export AZDO_PAT_TOKEN="your-pat-token"
export AZDO_PROJECT_NAME="Your-Project-Name"
export GROQ_API_KEY="your-groq-key"  # Optional, for LLM enhancement

# 3. Or use .env file
cp .env.example .env
# Edit .env with your credentials
```

### Usage Examples

**Via CLI**:
```bash
bash .devcontainer/run-azdo-agent.sh -p "MyProject" -t "MyTeam"
```

**Via Python**:
```python
from AzDOAgent import AzDOBusinessRequirementsAgent

agent = AzDOBusinessRequirementsAgent(
    org_url="https://dev.azure.com/myorg",
    pat_token="your-pat",
    project_name="MyProject",
    team_name="MyTeam"
)
agent.run()
```

**Via MCP (with Claude/Copilot)**:
```bash
bash .devcontainer/start-mcp-server.sh
# Then connect Claude or Copilot to stdio endpoint
```

### Limitations & Boundaries

This agent **WILL NOT**:
- Modify Azure DevOps work items
- Commit code changes
- Access Azure DevOps without valid credentials
- Process non-Python codebases (limited analysis)
- Generate incorrect requirements without verification

This agent **REQUIRES**:
- Valid Azure DevOps PAT token with work item read permission
- Network access to dev.azure.com
- Python 3.10+ environment
- (Optional) GROQ API key for LLM enhancement

### Error Handling

The agent handles:
- Invalid credentials → Clear error message with validation tool suggestion
- Network issues → Retry logic with exponential backoff
- Missing codebase → Graceful fallback to work items only
- LLM unavailable → Manual summary generation
- Rate limiting → Caching and request throttling

### Integration Points

**Custom Triggers**:
1. Call `generate_business_requirements()` for complete workflow
2. Chain with `fetch_work_items()` for incremental updates
3. Use `analyze_codebase()` standalone for code documentation
4. Verify setup with `validate_credentials()` before workflows

**AI Assistant Integration**:
- Start MCP server: `bash .devcontainer/start-mcp-server.sh`
- Tools available to Claude, Copilot, and other MCP-compatible clients
- Supports async tool invocation for concurrent requests

### Output Examples

Generated `BUSINESS_REQUIREMENTS.md`:
```markdown
# Business Requirements - MyProject

## Overview
[Summary from work items]

## Scope
[Features and deliverables]

## Technical Architecture
[Codebase analysis results]

## Work Items
[Linked work items with details]

## Dependencies
[Inter-project and external dependencies]
```

### Next Steps

1. Run health check: `bash .devcontainer/health-check.sh`
2. Validate credentials: `python -c "from AzDOAgent import ...; ..."`
3. Generate first requirements: `bash .devcontainer/run-azdo-agent.sh`
4. Review output: `cat BUSINESS_REQUIREMENTS.md`
5. Integrate with AI: Start MCP server and connect client