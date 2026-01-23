#!/bin/bash

# Discharge Summary Generator - Azure DevOps Agent Runner
# Runs the business requirements agent to fetch work items and generate documentation

set -e

echo "================================"
echo "Azure DevOps Agent"
echo "Business Requirements Generator"
echo "================================"
echo ""

# Check if Azure DevOps credentials are configured
if [ -z "$AZDO_ORG_URL" ] || [ -z "$AZDO_PAT_TOKEN" ] || [ -z "$AZDO_PROJECT_NAME" ]; then
    echo "⚠️  Warning: Azure DevOps credentials not fully configured"
    echo ""
    echo "To enable Azure DevOps integration, set the following environment variables:"
    echo "  export AZDO_ORG_URL='https://dev.azure.com/your-organization'"
    echo "  export AZDO_PAT_TOKEN='your-personal-access-token'"
    echo "  export AZDO_PROJECT_NAME='your-project-name'"
    echo "  export GROQ_API_KEY='your-groq-api-key'  (optional, for LLM-powered summaries)"
    echo ""
    echo "Or provide them as arguments to this script."
    echo ""
fi

# Parse command line arguments
ORG_URL=${1:-$AZDO_ORG_URL}
PAT_TOKEN=${2:-$AZDO_PAT_TOKEN}
PROJECT_NAME=${3:-$AZDO_PROJECT_NAME}
CODEBASE_DIR=${4:-.}
OUTPUT_FILE=${5:-BUSINESS_REQUIREMENTS.md}

# Run the agent
echo "Running Azure DevOps Agent..."
echo "  Organization: $ORG_URL"
echo "  Project: $PROJECT_NAME"
echo "  Codebase: $CODEBASE_DIR"
echo "  Output: $OUTPUT_FILE"
echo ""

python AzDOAgent.py \
    --org-url "$ORG_URL" \
    --pat-token "$PAT_TOKEN" \
    --project "$PROJECT_NAME" \
    --codebase "$CODEBASE_DIR" \
    --output "$OUTPUT_FILE"

echo ""
echo "✓ Agent execution completed!"
