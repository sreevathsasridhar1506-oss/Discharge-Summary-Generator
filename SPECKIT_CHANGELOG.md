# Spec-Kit Changelog

This file tracks changes to the repository's specifications and their mapping to code.

## Initial Adoption
- **Specs**: Added `specs/main_spec.yaml` to describe repository features and generation rules.
- **Devcontainer**: Created `.devcontainer/devcontainer.json` for Codespaces support.
- **MCP Server**: Implemented under `mcp/` with endpoints for file operations, git commands, and shell commands.
- **CI**: Added GitHub Actions workflow to validate the devcontainer and MCP server.