from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import urllib.parse
from sqlalchemy import create_engine, Column, String, Text, Integer, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
from contextlib import contextmanager
import enum

# --- DATABASE CONFIGURATION ---
DB_USER = "root"
DB_PASSWORD = urllib.parse.quote_plus("Johncena@15")
DB_HOST = "localhost"
DB_NAME = "tdm_orchestrator_system"

connection_uri = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(connection_uri, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ENUMS ---
class RequestStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# --- DATABASE MODELS ---

class RequestDB(Base):
    __tablename__ = "requests"
    
    request_id = Column(Integer, primary_key=True, autoincrement=True)
    requestor = Column(String(200), nullable=False)
    requesting_team = Column(String(200), nullable=False)
    requesting_timestamp = Column(TIMESTAMP, server_default=func.now())
    status = Column(String(50), default="NEW")
    scenario_type = Column(String(200), nullable=False)
    priority = Column(String(50), default="MEDIUM")
    comments = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class ScenarioDB(Base):
    __tablename__ = "scenarios"
    
    scenario_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_desc = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class TaskLogDB(Base):
    __tablename__ = "tasklog"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.scenario_id'), nullable=False)
    scenario = Column(String(200), nullable=False)
    task_id = Column(Integer, nullable=False)
    task_desc = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING")
    agent = Column(String(100), default="CDF_Agent")
    tool = Column(String(100), nullable=True)

class StatusLogDB(Base):
    __tablename__ = "status_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey('requests.request_id'), nullable=False)
    scenario_id = Column(Integer, ForeignKey('scenarios.scenario_id'), nullable=False)
    task_id = Column(Integer, nullable=False)
    task_desc = Column(Text, nullable=False)
    status_of_task = Column(String(50), default="PENDING")
    next_task = Column(Integer, nullable=True)
    previous_task = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")

# --- DATABASE HELPER FUNCTIONS ---

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PYDANTIC MODELS ---

class ScenarioCreate(BaseModel):
    scenario_desc: str

class TaskCreate(BaseModel):
    scenario_id: int
    scenario: str
    task_id: int
    task_desc: str
    agent: str = "CDF_Agent"
    tool: Optional[str] = None

class RequestCreate(BaseModel):
    requestor: str
    requesting_team: str
    scenario_type: str
    priority: str = "MEDIUM"
    comments: Optional[str] = None

# --- FASTAPI APP ---

app = FastAPI(
    title="TDM Orchestrator Setup API",
    description="API for setting up scenarios, tasks, and requests",
    version="1.0.0"
)

# --- SCENARIO ENDPOINTS ---

@app.post("/scenarios", tags=["Scenarios"])
def create_scenario(scenario: ScenarioCreate):
    """Create a new scenario"""
    with get_db() as db:
        new_scenario = ScenarioDB(
            scenario_desc=scenario.scenario_desc
        )
        db.add(new_scenario)
        db.commit()
        db.refresh(new_scenario)
        
        return {
            "message": "Scenario created successfully",
            "scenario_id": new_scenario.scenario_id,
            "scenario_desc": new_scenario.scenario_desc
        }

@app.get("/scenarios", tags=["Scenarios"])
def get_all_scenarios():
    """Get all scenarios"""
    with get_db() as db:
        scenarios = db.query(ScenarioDB).all()
        return {
            "scenarios": [
                {
                    "scenario_id": s.scenario_id,
                    "scenario_desc": s.scenario_desc,
                    "created_at": str(s.created_at)
                } for s in scenarios
            ]
        }

@app.get("/scenarios/{scenario_id}", tags=["Scenarios"])
def get_scenario(scenario_id: int):
    """Get a specific scenario"""
    with get_db() as db:
        scenario = db.query(ScenarioDB).filter(ScenarioDB.scenario_id == scenario_id).first()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        return {
            "scenario_id": scenario.scenario_id,
            "scenario_desc": scenario.scenario_desc,
            "created_at": str(scenario.created_at)
        }

# --- TASK ENDPOINTS ---

@app.post("/tasks", tags=["Tasks"])
def create_task(task: TaskCreate):
    """Create a new task for a scenario"""
    with get_db() as db:
        # Verify scenario exists
        scenario = db.query(ScenarioDB).filter(ScenarioDB.scenario_id == task.scenario_id).first()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        new_task = TaskLogDB(
            scenario_id=task.scenario_id,
            scenario=task.scenario,
            task_id=task.task_id,
            task_desc=task.task_desc,
            agent=task.agent,
            tool=task.tool
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        
        return {
            "message": "Task created successfully",
            "log_id": new_task.log_id,
            "scenario_id": new_task.scenario_id,
            "task_id": new_task.task_id,
            "task_desc": new_task.task_desc
        }

@app.post("/tasks/bulk", tags=["Tasks"])
def create_bulk_tasks(tasks: List[TaskCreate]):
    """Create multiple tasks at once"""
    with get_db() as db:
        created_tasks = []
        for task in tasks:
            # Verify scenario exists
            scenario = db.query(ScenarioDB).filter(ScenarioDB.scenario_id == task.scenario_id).first()
            if not scenario:
                raise HTTPException(status_code=404, detail=f"Scenario {task.scenario_id} not found")
            
            new_task = TaskLogDB(
                scenario_id=task.scenario_id,
                scenario=task.scenario,
                task_id=task.task_id,
                task_desc=task.task_desc,
                agent=task.agent,
                tool=task.tool
            )
            db.add(new_task)
            created_tasks.append({
                "task_id": task.task_id,
                "task_desc": task.task_desc
            })
        
        db.commit()
        
        return {
            "message": f"{len(created_tasks)} tasks created successfully",
            "tasks": created_tasks
        }

@app.get("/tasks/scenario/{scenario_id}", tags=["Tasks"])
def get_tasks_by_scenario(scenario_id: int):
    """Get all tasks for a scenario"""
    with get_db() as db:
        tasks = db.query(TaskLogDB).filter(TaskLogDB.scenario_id == scenario_id).order_by(TaskLogDB.task_id).all()
        
        return {
            "scenario_id": scenario_id,
            "total_tasks": len(tasks),
            "tasks": [
                {
                    "log_id": t.log_id,
                    "task_id": t.task_id,
                    "task_desc": t.task_desc,
                    "status": t.status,
                    "agent": t.agent,
                    "tool": t.tool
                } for t in tasks
            ]
        }

# --- REQUEST ENDPOINTS ---

@app.post("/requests", tags=["Requests"])
def create_request(request: RequestCreate):
    """Create a new request"""
    with get_db() as db:
        new_request = RequestDB(
            requestor=request.requestor,
            requesting_team=request.requesting_team,
            scenario_type=request.scenario_type,
            priority=request.priority,
            comments=request.comments,
            status="NEW"
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        return {
            "message": "Request created successfully",
            "request_id": new_request.request_id,
            "requestor": new_request.requestor,
            "scenario_type": new_request.scenario_type,
            "status": new_request.status,
            "next_step": "Use this request_id to start orchestration workflow"
        }

@app.get("/requests", tags=["Requests"])
def get_all_requests():
    """Get all requests"""
    with get_db() as db:
        requests = db.query(RequestDB).order_by(RequestDB.created_at.desc()).all()
        
        return {
            "requests": [
                {
                    "request_id": r.request_id,
                    "requestor": r.requestor,
                    "requesting_team": r.requesting_team,
                    "scenario_type": r.scenario_type,
                    "status": r.status,
                    "priority": r.priority,
                    "created_at": str(r.created_at)
                } for r in requests
            ]
        }

@app.get("/requests/{request_id}", tags=["Requests"])
def get_request(request_id: int):
    """Get a specific request"""
    with get_db() as db:
        request = db.query(RequestDB).filter(RequestDB.request_id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return {
            "request_id": request.request_id,
            "requestor": request.requestor,
            "requesting_team": request.requesting_team,
            "scenario_type": request.scenario_type,
            "status": request.status,
            "priority": request.priority,
            "comments": request.comments,
            "created_at": str(request.created_at),
            "updated_at": str(request.updated_at)
        }

# --- INITIALIZATION ENDPOINT ---

@app.post("/initialize/cdf-refresh", tags=["Initialization"])
def initialize_cdf_refresh_scenario():
    """Initialize the CDF Refresh scenario with all 15 tasks"""
    with get_db() as db:
        # Check if scenario already exists
        existing = db.query(ScenarioDB).filter(ScenarioDB.scenario_desc == "CDF Refresh").first()
        if existing:
            return {
                "message": "CDF Refresh scenario already exists",
                "scenario_id": existing.scenario_id
            }
        
        # Create scenario
        scenario = ScenarioDB(scenario_desc="CDF Refresh")
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        
        # Create 15 tasks for CDF Refresh
        tasks = [
            {"task_id": 1, "task_desc": "Validate source data availability"},
            {"task_id": 2, "task_desc": "Backup current CDF environment"},
            {"task_id": 3, "task_desc": "Stop dependent services"},
            {"task_id": 4, "task_desc": "Clear cache and temporary files"},
            {"task_id": 5, "task_desc": "Extract data from source systems"},
            {"task_id": 6, "task_desc": "Transform data according to specifications"},
            {"task_id": 7, "task_desc": "Validate transformed data quality"},
            {"task_id": 8, "task_desc": "Load data into staging environment"},
            {"task_id": 9, "task_desc": "Run data validation scripts"},
            {"task_id": 10, "task_desc": "Submit a service now ticket"},  # This will be the waiting task
            {"task_id": 11, "task_desc": "Promote data to production CDF"},
            {"task_id": 12, "task_desc": "Restart dependent services"},
            {"task_id": 13, "task_desc": "Run smoke tests"},
            {"task_id": 14, "task_desc": "Generate refresh completion report"},
            {"task_id": 15, "task_desc": "Notify stakeholders of completion"}
        ]
        
        for task_data in tasks:
            task = TaskLogDB(
                scenario_id=scenario.scenario_id,
                scenario="CDF Refresh",
                task_id=task_data["task_id"],
                task_desc=task_data["task_desc"],
                agent="CDF_Agent",
                tool="TDM_Tool" if task_data["task_id"] != 10 else "ServiceNow"
            )
            db.add(task)
        
        db.commit()
        
        return {
            "message": "CDF Refresh scenario initialized successfully",
            "scenario_id": scenario.scenario_id,
            "total_tasks": len(tasks),
            "tasks": tasks
        }

# --- HEALTH CHECK ---

@app.get("/health", tags=["System"])
def health_check():
    """Health check"""
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/", tags=["Root"])
def read_root():
    """API information"""
    return {
        "name": "TDM Orchestrator Setup API",
        "version": "1.0.0",
        "description": "Setup API for scenarios, tasks, and requests",
        "key_endpoints": {
            "initialize_cdf": "POST /initialize/cdf-refresh",
            "create_scenario": "POST /scenarios",
            "create_task": "POST /tasks",
            "create_bulk_tasks": "POST /tasks/bulk",
            "create_request": "POST /requests",
            "get_scenarios": "GET /scenarios",
            "get_tasks": "GET /tasks/scenario/{scenario_id}",
            "get_requests": "GET /requests"
        },
        "quick_start": [
            "1. Run POST /initialize/cdf-refresh to create CDF Refresh scenario",
            "2. Run POST /requests to create a new request",
            "3. Use the request_id in the orchestrator program"
        ],
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("TT:app", host="0.0.0.0", port=8001, reload=True)