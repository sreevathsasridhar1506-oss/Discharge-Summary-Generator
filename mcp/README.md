# MCP Server

This directory contains the implementation of the MCP (Model Context Protocol) server for the Discharge Summary Generator repository.

## Features
- **File System Operations**: Read file contents.
- **System Commands**: Run shell commands and capture output.
- **Git Operations**: Create branches and open pull requests.

## How to Run

### Using Docker Compose
1. Navigate to the `mcp/` directory.
2. Run the following command:
   ```bash
   docker-compose up
   ```
3. The server will be available at `http://localhost:8080`.

### Endpoints
- `GET /file_system/read`: Read the contents of a file.
- `POST /system/run`: Run a shell command.
- `POST /git/create_branch`: Create a new Git branch.
- `POST /git/open_pr`: Open a pull request.