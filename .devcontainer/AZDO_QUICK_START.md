# Azure DevOps Agent - Quick Start Guide

## 5-Minute Setup

### Step 1: Get Your Azure DevOps PAT Token (2 min)

1. Go to https://dev.azure.com
2. Click your profile icon → **Personal access tokens**
3. Click **New Token**
4. Fill in:
   - Name: "Codespace Agent"
   - Scopes: Select **Work Items (Read)** and **Project & Team (Read)**
   - Expiration: 90 days
5. Copy the token (you won't see it again!)

### Step 2: Configure Environment Variables (2 min)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
AZDO_ORG_URL=https://dev.azure.com/your-organization
AZDO_PAT_TOKEN=paste-your-token-here
AZDO_PROJECT_NAME=YourProjectName
GROQ_API_KEY=your-groq-key-optional
```

### Step 3: Run the Agent (1 min)

```bash
bash .devcontainer/run-azdo-agent.sh
```

Done! Check `BUSINESS_REQUIREMENTS.md` for your generated requirements.

---

## What the Agent Does

```
┌─────────────────────────────────────────────────────────┐
│          Azure DevOps Business Requirements Agent       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Connects to Azure DevOps                           │
│     └─ Fetches work items (Features, Bugs, etc.)      │
│                                                         │
│  2. Analyzes Your Codebase                            │
│     ├─ Python modules and classes                     │
│     ├─ Data models and structures                     │
│     └─ Dependencies and tech stack                    │
│                                                         │
│  3. Generates Business Requirements                   │
│     ├─ Executive Summary                             │
│     ├─ Work Items Breakdown                          │
│     ├─ Technical Architecture                        │
│     └─ Technology Stack Details                      │
│                                                         │
│  4. Saves as Markdown                                │
│     └─ BUSINESS_REQUIREMENTS.md                      │
│        (Perfect for documentation!)                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### In Codespace Terminal

```bash
# Run with default settings
bash .devcontainer/run-azdo-agent.sh

# Run with custom output file
bash .devcontainer/run-azdo-agent.sh \
  "https://dev.azure.com/myorg" \
  "mytoken" \
  "MyProject" \
  "." \
  "requirements-2026-01-23.md"

# Or use Python directly
python AzDOAgent.py --output "REQUIREMENTS.md"
```

### In Python Code

```python
from AzDOAgent import AzDOBusinessRequirementsAgent
import os

# Using environment variables
agent = AzDOBusinessRequirementsAgent()

# Or with explicit parameters
agent = AzDOBusinessRequirementsAgent(
    organization_url="https://dev.azure.com/myorg",
    pat_token=os.getenv("AZDO_PAT_TOKEN"),
    project_name="MyProject",
    groq_api_key=os.getenv("GROQ_API_KEY")
)

# Generate requirements
path = agent.run(
    codebase_dir=".",
    output_path="BUSINESS_REQUIREMENTS.md"
)

print(f"Generated: {path}")
```

---

## Example Output

The agent generates a professional markdown document:

```markdown
# Business Requirements Summary

*Generated: 2026-01-23 14:30:00*

## Executive Summary

This project comprises 15 Python modules with 8 data models 
for medical discharge summarization using AI.

## Azure DevOps Work Items

### Features (3)
- **Implement LangGraph Orchestration** (ID: 42, State: Active)
- **Add Azure DevOps Integration** (ID: 45, State: Closed)

### User Stories (2)
- **As a clinician, I need to process discharge transcripts** (ID: 38)

## Technical Architecture

### Modules (15)
- main.py - FastAPI application
- AzDOAgent.py - Business requirements agent
- CENTRALORCH.py - LangGraph orchestration
- ... (12 more)

## Technology Stack
- fastapi - Web framework
- langchain - LLM orchestration
- azure-devops - Azure DevOps API
- uvicorn - ASGI server
- pydantic - Data validation
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Credentials not configured" | Run `cp .env.example .env` and fill in values |
| "No work items found" | Verify project name matches exactly in Azure DevOps |
| "Permission denied" | Ensure PAT token has "Work Items (Read)" scope |
| "ModuleNotFoundError" | Run `pip install -r requirements.txt.txt` |
| "LLM features not working" | GROQ_API_KEY is optional; agent works without it |

---

## Security Notes

🔒 **Keep Your Credentials Safe**

- ✓ `.env` is in `.gitignore` (won't be committed)
- ✓ Never share your PAT token
- ✓ Use Codespace secrets for sensitive data
- ✓ Rotate tokens regularly

**Set Codespace Secrets:**
1. Go to repository → Settings → Secrets and variables → Codespaces
2. Add: `AZDO_ORG_URL`, `AZDO_PAT_TOKEN`, `AZDO_PROJECT_NAME`
3. In Codespace, they're available as environment variables

---

## Advanced Usage

### Integration with CI/CD

Add to your GitHub Actions workflow:

```yaml
- name: Generate Business Requirements
  run: |
    python AzDOAgent.py \
      --org-url ${{ secrets.AZDO_ORG_URL }} \
      --pat-token ${{ secrets.AZDO_PAT_TOKEN }} \
      --project ${{ secrets.AZDO_PROJECT_NAME }} \
      --output "docs/BUSINESS_REQUIREMENTS.md"

- name: Commit Changes
  run: |
    git add docs/BUSINESS_REQUIREMENTS.md
    git commit -m "Updated business requirements" || true
```

### Filter Specific Work Item Types

Modify `AzDOAgent.py` to customize the WIQL query:

```python
query = f"""
SELECT [System.Id], [System.Title], [System.State]
FROM workitems
WHERE [System.TeamProject] = '{self.project_name}'
AND [System.WorkItemType] IN ('Feature', 'User Story')
AND [System.State] <> 'Removed'
"""
```

### Combine with Auto-Generated API Docs

The generated requirements work perfectly with:
- FastAPI OpenAPI/Swagger docs (at `/docs`)
- Markdown documentation
- GitHub Pages wikis
- Confluence documentation

---

## Next Steps

1. ✅ Generate your first business requirements document
2. 📖 Add it to your repository's documentation
3. 🔄 Set up automated generation in CI/CD
4. 💡 Customize prompts for your business domain
5. 🤝 Share with stakeholders and team

---

## Documentation

- Full setup guide: [AZDO_AGENT_SETUP.md](AZDO_AGENT_SETUP.md)
- Codespace setup: [CODESPACE_SETUP.md](CODESPACE_SETUP.md)
- FastAPI startup: Check `start.sh`

---

## Support

- 📚 [Azure DevOps API Docs](https://learn.microsoft.com/en-us/azure/devops/integrate/concepts/rest-api-overview)
- 🤖 [GROQ LLM Documentation](https://console.groq.com/docs)
- 🚀 [GitHub Codespaces Guide](https://docs.github.com/en/codespaces)

---

**Happy requirements generating! 🚀**
