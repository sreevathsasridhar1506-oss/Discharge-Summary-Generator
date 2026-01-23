#!/bin/bash

# Discharge Summary Generator - Azure DevOps Agent Health Check
# Verifies that the environment is properly configured for the agent

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Azure DevOps Agent - Health Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Counter for checks
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

# Function to print check results
check_status() {
    local check_name=$1
    local status=$2
    local message=$3
    
    if [ "$status" = "pass" ]; then
        echo -e "${GREEN}✓${NC} $check_name"
        ((CHECKS_PASSED++))
    elif [ "$status" = "fail" ]; then
        echo -e "${RED}✗${NC} $check_name"
        [ -n "$message" ] && echo -e "  ${RED}Error: $message${NC}"
        ((CHECKS_FAILED++))
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}⚠${NC} $check_name"
        [ -n "$message" ] && echo -e "  ${YELLOW}Warning: $message${NC}"
        ((CHECKS_WARNED++))
    fi
}

echo -e "${BLUE}1. Python Environment${NC}"
echo "---"

# Check Python installation
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    check_status "Python 3 Installation" "pass" ""
    echo "  Version: $PYTHON_VERSION"
else
    check_status "Python 3 Installation" "fail" "Python 3 not found"
fi

# Check pip
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    check_status "pip Installation" "pass" ""
else
    check_status "pip Installation" "fail" "pip not found"
fi

echo ""
echo -e "${BLUE}2. Dependencies${NC}"
echo "---"

# Check required Python packages
REQUIRED_PACKAGES=("azure.devops" "langchain" "langchain_groq" "fastapi" "uvicorn" "pydantic")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package}" 2>/dev/null; then
        check_status "$package Package" "pass" ""
    else
        check_status "$package Package" "fail" "Not installed"
    fi
done

echo ""
echo -e "${BLUE}3. Configuration Files${NC}"
echo "---"

# Check for .env file
if [ -f ".env" ]; then
    check_status ".env File" "pass" ""
else
    check_status ".env File" "warn" "Not found (copy from .env.example)"
fi

# Check for requirements.txt
if [ -f "requirements.txt.txt" ]; then
    check_status "requirements.txt.txt" "pass" ""
else
    check_status "requirements.txt.txt" "fail" "Not found"
fi

# Check for agent script
if [ -f "AzDOAgent.py" ]; then
    check_status "AzDOAgent.py Script" "pass" ""
else
    check_status "AzDOAgent.py Script" "fail" "Not found"
fi

echo ""
echo -e "${BLUE}4. Azure DevOps Configuration${NC}"
echo "---"

# Check Azure DevOps environment variables
if [ -n "$AZDO_ORG_URL" ]; then
    check_status "AZDO_ORG_URL" "pass" "$AZDO_ORG_URL"
else
    check_status "AZDO_ORG_URL" "warn" "Not set (required for AzDO features)"
fi

if [ -n "$AZDO_PAT_TOKEN" ]; then
    TOKEN_LENGTH=${#AZDO_PAT_TOKEN}
    MASKED_TOKEN="${AZDO_PAT_TOKEN:0:5}...${AZDO_PAT_TOKEN: -5}"
    check_status "AZDO_PAT_TOKEN" "pass" "$MASKED_TOKEN ($TOKEN_LENGTH chars)"
else
    check_status "AZDO_PAT_TOKEN" "warn" "Not set (required for AzDO features)"
fi

if [ -n "$AZDO_PROJECT_NAME" ]; then
    check_status "AZDO_PROJECT_NAME" "pass" "$AZDO_PROJECT_NAME"
else
    check_status "AZDO_PROJECT_NAME" "warn" "Not set (required for AzDO features)"
fi

echo ""
echo -e "${BLUE}5. Optional Features${NC}"
echo "---"

# Check GROQ API Key
if [ -n "$GROQ_API_KEY" ]; then
    check_status "GROQ_API_KEY" "pass" "Configured (LLM features enabled)"
else
    check_status "GROQ_API_KEY" "warn" "Not set (optional, for LLM-powered summaries)"
fi

echo ""
echo -e "${BLUE}6. Network Connectivity${NC}"
echo "---"

# Check internet connectivity
if timeout 5 curl -s -o /dev/null -w "%{http_code}" "https://api.github.com" &>/dev/null; then
    check_status "Internet Connectivity" "pass" ""
else
    check_status "Internet Connectivity" "warn" "Cannot reach external services"
fi

# Check Azure DevOps endpoint (if credentials are set)
if [ -n "$AZDO_ORG_URL" ] && [ -n "$AZDO_PAT_TOKEN" ]; then
    if timeout 5 curl -s -o /dev/null -w "%{http_code}" "$AZDO_ORG_URL" &>/dev/null; then
        check_status "Azure DevOps Connectivity" "pass" ""
    else
        check_status "Azure DevOps Connectivity" "fail" "Cannot reach $AZDO_ORG_URL"
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Health Check Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${GREEN}Passed: $CHECKS_PASSED${NC}"
echo -e "${YELLOW}Warnings: $CHECKS_WARNED${NC}"
echo -e "${RED}Failed: $CHECKS_FAILED${NC}"

echo ""

if [ $CHECKS_FAILED -eq 0 ] && [ $CHECKS_WARNED -eq 0 ]; then
    echo -e "${GREEN}✓ All systems operational!${NC}"
    echo ""
    echo "You can now run the agent:"
    echo "  bash .devcontainer/run-azdo-agent.sh"
    exit 0
elif [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ System operational with warnings${NC}"
    echo ""
    echo "The agent will run, but some features may be limited."
    echo "To enable all features, address the warnings above."
    exit 0
else
    echo -e "${RED}✗ System not ready for agent execution${NC}"
    echo ""
    echo "Please fix the failed checks above."
    echo ""
    echo "Next steps:"
    echo "1. Install missing dependencies: pip install -r requirements.txt.txt"
    echo "2. Configure Azure DevOps: cp .env.example .env && edit .env"
    echo "3. Re-run this health check: bash .devcontainer/health-check.sh"
    exit 1
fi
