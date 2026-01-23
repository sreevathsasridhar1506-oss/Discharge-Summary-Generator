# Discharge Summary Generator

This repository provides tools for generating discharge summaries using AI models. It includes a Spec-Kit driven structure, a development container for reproducibility, and an MCP server for tool integration.

## Features
- **Spec-Kit Integration**: Specifications for repository features and generation rules.
- **Devcontainer**: Reproducible development environment for Codespaces.
- **MCP Server**: Provides endpoints for file operations, git commands, and more.

## Getting Started

### Codespaces
1. Open the repository in a GitHub Codespace.
2. The devcontainer will automatically set up the environment.

### Running the MCP Server
1. Navigate to the `mcp/` directory.
2. Run the server using Docker Compose:
   ```bash
   docker-compose up
   ```
3. Access the server at `http://localhost:8080`.

### Regenerating Code
Use the Spec-Kit CLI to regenerate code based on updated specs:
```bash
speckit generate specs/main_spec.yaml
```

## Contributing
See `SPECKIT_CHANGELOG.md` for a summary of spec changes and their mapping to code.