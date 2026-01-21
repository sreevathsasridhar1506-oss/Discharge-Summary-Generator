# API.py - FastAPI Application

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Import custom modules
from DB import get_db, check_table_exists, get_table_statistics, get_sample_data, get_connection_uri
from SQLDBAgent1 import SQLDatabaseAgent

# --- PYDANTIC MODELS ---
class DeviationResponse(BaseModel):
    total_retrieve_fields: int
    total_fill_fields: int
    filled_retrieve_fields: int
    filled_fill_fields: int
    deviation_percentage: float
    message: str


class QueryRequest(BaseModel):
    question: str


# --- CONFIGURATION ---
GROQ_API_KEY = "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"
TABLE_NAME = "from_environment"

# --- INITIALIZE SQL AGENT ---
connection_uri = get_connection_uri()
sql_agent = SQLDatabaseAgent(
    connection_uri=connection_uri,
    api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile"
)

# --- FASTAPI APP ---
app = FastAPI(
    title="SQL Agent - Deviation Analysis",
    description="SQL Agent to calculate deviation between retrieval and filling processes using comprehensive prompts",
    version="2.0.0"
)

# --- API ENDPOINTS ---

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "SQL Agent - Deviation Analysis API", 
        "status": "Running",
        "version": "2.0.0 - Modular Architecture with create_agent and SQLDatabaseToolkit"
    }


@app.post("/analyze-deviation", response_model=DeviationResponse)
async def analyze_deviation():
    """
    Analyze deviation between retrieval and filling processes using a comprehensive prompt.
    
    The SQL Agent receives a detailed prompt explaining:
    - The data structure and columns
    - What needs to be analyzed (retrieval vs filling processes)
    - How to identify properly filled fields
    - The deviation formula to calculate
    
    The agent then autonomously performs the analysis and returns the results.
    
    Returns:
        DeviationResponse: Deviation analysis results
    """
    # Check if from_environment table has data
    if not check_table_exists(TABLE_NAME):
        raise HTTPException(status_code=404, detail=f"No data found in {TABLE_NAME} table")
    
    # Calculate deviation using SQL Agent
    try:
        result = sql_agent.calculate_deviation()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deviation calculation failed: {str(e)}")


@app.post("/custom-query")
async def custom_query(request: QueryRequest):
    """
    Execute a custom natural language SQL query using the agent.
    
    Args:
        request: QueryRequest with the natural language question
        
    Returns:
        dict: Query results with question and answer
    """
    try:
        answer = sql_agent.query(request.question)
        
        return {
            "question": request.question,
            "answer": answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/view-retrieval-data")
async def view_retrieval_data(limit: int = 10):
    """
    View sample records from from_environment where process = 'retrieval'.
    
    Args:
        limit: Number of records to return (default: 10)
        
    Returns:
        dict: Sample retrieval records
    """
    try:
        records = get_sample_data(TABLE_NAME, "retrieval", limit)
        
        return {
            "process": "retrieval",
            "sample_records": records,
            "count": len(records)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")


@app.get("/view-filling-data")
async def view_filling_data(limit: int = 10):
    """
    View sample records from from_environment where process = 'filling'.
    
    Args:
        limit: Number of records to return (default: 10)
        
    Returns:
        dict: Sample filling records
    """
    try:
        records = get_sample_data(TABLE_NAME, "filling", limit)
        
        return {
            "process": "filling",
            "sample_records": records,
            "count": len(records)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")


@app.get("/table-info")
async def get_table_info():
    """
    Get schema information about the database tables.
    
    Returns:
        dict: Database schema information
    """
    try:
        schema_info = sql_agent.get_schema_info()
        return {
            "schema": schema_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get table info: {str(e)}")


@app.get("/statistics")
async def get_statistics():
    """
    Get basic statistics about the from_environment table.
    
    Returns:
        dict: Table statistics including counts by process type
    """
    try:
        stats = get_table_statistics(TABLE_NAME)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "database": "connected",
        "agent": "initialized"
    }


if __name__ == "__main__":
    uvicorn.run("API:app", host="0.0.0.0", port=8001, reload=True)