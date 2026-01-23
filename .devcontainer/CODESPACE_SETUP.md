# Codespace Setup Guide

This project is configured to automatically set up and run in GitHub Codespaces.

## Automatic Setup (on Codespace Creation)

When you create a new Codespace, the following happens automatically:

1. **Container Initialization** - Python 3.12 development container is created
2. **Dependencies Installation** - All Python dependencies from `requirements.txt.txt` are installed
3. **Extensions Installation** - Recommended VS Code extensions are installed:
   - Python extension
   - Pylance (Python language server)
   - Python debugger
   - Ruff (Python linter/formatter)

The entire setup is automated through `.devcontainer/devcontainer.json` and `.devcontainer/postCreateCommand.sh`.

## Starting the FastAPI Application

After the Codespace is created and setup is complete, you have two options:

### Option 1: Using the Startup Script
```bash
bash .devcontainer/start.sh
```

### Option 2: Running Uvicorn Directly
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Accessing the Application

Once the FastAPI server is running:

- **Main API**: http://localhost:8000
- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

## Port Forwarding

Port 8000 is automatically forwarded in your Codespace. You'll receive a notification when the port is accessed for the first time.

## Project Structure

```
.devcontainer/
├── devcontainer.json      # Codespace configuration
├── postCreateCommand.sh    # Runs automatically after container creation
└── start.sh               # Script to start the FastAPI application
```

## Requirements

All dependencies are defined in `requirements.txt.txt`:
- fastapi
- uvicorn[standard]
- langchain>=1.0.0
- langchain-community>=0.3.0
- langchain-google-genai>=2.0.0
- google-generativeai
- pydantic>=2.7,<3.0

## Troubleshooting

### Dependencies not installed?
Manually install dependencies:
```bash
pip install -r requirements.txt.txt
```

### Port 8000 already in use?
Change the port in the start.sh script or run:
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Want to modify startup behavior?
Edit `.devcontainer/postCreateCommand.sh` for post-creation tasks or `.devcontainer/start.sh` for application startup.
