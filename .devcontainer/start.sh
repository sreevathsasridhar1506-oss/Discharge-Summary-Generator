#!/bin/bash

# Discharge Summary Generator - FastAPI Startup Script
# Starts the FastAPI application with uvicorn

set -e

echo "Starting Discharge Summary Generator FastAPI Application..."
echo "Server will be available at: http://localhost:8000"
echo "API docs will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the FastAPI application with uvicorn
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
