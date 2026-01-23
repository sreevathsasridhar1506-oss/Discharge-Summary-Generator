# Azure DevOps Business Requirements Agent

This agent connects to Azure DevOps to fetch work items and analyzes your codebase to generate a comprehensive business requirements summary in markdown format.

## Features

- 🔗 **Azure DevOps Integration** - Connects to your AzDO project and retrieves work items
- 📊 **Codebase Analysis** - Scans Python modules, data models, and components
- 🤖 **LLM-Powered Summaries** - Uses GROQ LLM to generate professional requirements documents
- 📄 **Markdown Output** - Generates well-formatted markdown suitable for documentation
- 🐳 **Codespace Ready** - Fully integrated with GitHub Codespace standards

## Setup Instructions

### 1. Configure Azure DevOps Credentials

You need to configure three environment variables:

#### Method 1: Set Environment Variables Directly

```bash
export AZDO_ORG_URL="https://dev.azure.com/your-organization"
export AZDO_PAT_TOKEN="your-personal-access-token"
export AZDO_PROJECT_NAME="your-project-name"
export GROQ_API_KEY="your-groq-api-key"  # Optional, for LLM features
```

#### Method 2: Create `.env` File (Recommended for Codespace)

Create a `.env` file in the workspace root:

```env
AZDO_ORG_URL=https://dev.azure.com/your-organization
AZDO_PAT_TOKEN=your-personal-access-token
AZDO_PROJECT_NAME=your-project-name
GROQ_API_KEY=your-groq-api-key
```

**Note:** The `.env` file is Git-ignored for security. Never commit credentials to the repository.

### 2. Get Your Azure DevOps Personal Access Token (PAT)

1. Go to https://dev.azure.com
2. Sign in to your organization
3. Click your profile icon → **Personal access tokens**
4. Click **New Token**
5. Create a token with the following scopes:
   - ✓ Work Items (Read)
   - ✓ Project & Team (Read)
6. Copy the generated token

### 3. Find Your Organization and Project Details

- **Organization URL**: `https://dev.azure.com/{your-organization-name}`
- **Project Name**: The exact name of your AzDO project

## Usage

### Option 1: Using the Runner Script

```bash
bash .devcontainer/run-azdo-agent.sh
```

With environment variables pre-configured, it will automatically fetch work items and generate the summary.

### Option 2: Manual Execution with Arguments

```bash
bash .devcontainer/run-azdo-agent.sh \
    "https://dev.azure.com/my-org" \
    "my-pat-token" \
    "MyProject" \
    "." \
    "BUSINESS_REQUIREMENTS.md"
```

### Option 3: Direct Python Execution

```bash
python AzDOAgent.py \
    --org-url "https://dev.azure.com/my-org" \
    --pat-token "my-pat-token" \
    --project "MyProject" \
    --output "BUSINESS_REQUIREMENTS.md"
```

With all environment variables set, simply run:

```bash
python AzDOAgent.py
```

## Output

The agent generates a `BUSINESS_REQUIREMENTS.md` file containing:

- **Executive Summary** - High-level overview of the project
- **Azure DevOps Work Items** - Organized by type (Features, Bugs, User Stories, etc.)
- **Technical Architecture** - Modules, data models, and components
- **Technology Stack** - Dependencies and frameworks used
- **Success Criteria** - Based on work items and objectives

## Agent Components

### AzDOBusinessRequirementsAgent Class

Main agent class with the following methods:

- `__init__()` - Initialize with AzDO and LLM configuration
- `fetch_work_items()` - Retrieve work items from Azure DevOps
- `analyze_codebase()` - Scan and analyze Python codebase
- `generate_requirements_summary()` - Create business requirements document
- `save_summary_to_file()` - Write output to markdown file
- `run()` - Execute complete workflow

### Example Usage in Python Code

```python
from AzDOAgent import AzDOBusinessRequirementsAgent

# Initialize agent
agent = AzDOBusinessRequirementsAgent(
    organization_url="https://dev.azure.com/my-org",
    pat_token="my-pat-token",
    project_name="MyProject",
    groq_api_key="my-groq-key",
)

# Run agent
output_path = agent.run(
    codebase_dir=".",
    output_path="BUSINESS_REQUIREMENTS.md"
)

print(f"Generated: {output_path}")
```

## Integration with Codespace

### Automatic Execution on Startup (Optional)

To have the agent run automatically when the Codespace starts, update `.devcontainer/postCreateCommand.sh`:

```bash
# Add this line to postCreateCommand.sh
bash .devcontainer/run-azdo-agent.sh 2>/dev/null || true
```

**Note:** Only do this if you have credentials configured.

### Manual Execution in Codespace

1. Start your Codespace
2. In the terminal, set credentials:
   ```bash
   export AZDO_ORG_URL="https://dev.azure.com/your-org"
   export AZDO_PAT_TOKEN="your-token"
   export AZDO_PROJECT_NAME="your-project"
   ```
3. Run the agent:
   ```bash
   bash .devcontainer/run-azdo-agent.sh
   ```

## Troubleshooting

### "Azure DevOps client not initialized"

- Check that `AZDO_ORG_URL`, `AZDO_PAT_TOKEN`, and `AZDO_PROJECT_NAME` are set correctly
- Verify the PAT token is still valid (not expired)
- Ensure the token has "Work Items (Read)" scope

### "No work items retrieved"

- Verify the project name exactly matches your AzDO project
- Check that your PAT token has access to the project
- The project may be empty or all work items removed

### "LLM features not working"

- `GROQ_API_KEY` may not be set - this is optional
- If not set, the agent will generate a summary without LLM enhancement
- Check your GROQ API key is valid

### "ImportError: No module named 'azure.devops'"

- Install dependencies: `pip install -r requirements.txt.txt`
- Or run in your Codespace (dependencies auto-installed on startup)

## Security Considerations

⚠️ **Important Security Notes:**

1. **Never commit credentials** to Git
2. Use Codespace secrets for sensitive data:
   - Go to repository Settings → Secrets and variables → Codespaces
   - Add `AZDO_PAT_TOKEN`, `AZDO_ORG_URL`, etc.
3. Pat tokens should have **minimal required scopes**
4. Rotate tokens regularly
5. Use `.env` file (which is in `.gitignore`) for local development

## API Reference

### fetch_work_items()

```python
work_items = agent.fetch_work_items()
# Returns: List[Dict] with keys: id, type, title, state, description, assigned_to
```

### analyze_codebase(root_dir)

```python
analysis = agent.analyze_codebase(".")
# Returns: Dict with modules, data_models, main_components, dependencies
```

### generate_requirements_summary(work_items, codebase_analysis)

```python
summary = agent.generate_requirements_summary(work_items, analysis)
# Returns: str (markdown formatted)
```

### save_summary_to_file(summary, output_path)

```python
path = agent.save_summary_to_file(summary, "OUTPUT.md")
# Returns: str (absolute path to saved file)
```

## Example Output Structure

```markdown
# Business Requirements Summary

*Generated: 2026-01-23 14:30:00*

## Executive Summary

This project comprises 15 Python modules with 8 data models.

## Azure DevOps Work Items

### Features (3)
- **User authentication system** (ID: 1234, State: Active)
- **Real-time data sync** (ID: 1235, State: Active)

## Technical Architecture

### Modules (15)
- `main.py`
- `AzDOAgent.py`
- `database.py`
...

## Technology Stack
- fastapi
- langchain
- azure-devops
...
```

## Contributing

To improve the agent:

1. Enhance the `analyze_codebase()` method for additional language support
2. Add support for other work item types
3. Improve LLM prompt templates
4. Add filtering options for work items

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review Azure DevOps API documentation
3. Check GROQ LLM documentation
