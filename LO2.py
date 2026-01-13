from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import re
import urllib.parse
import asyncio
import random
from sqlalchemy import create_engine, Column, String, Text, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
from contextlib import contextmanager

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- DATABASE CONFIGURATION ---
DB_USER = "root"
DB_PASSWORD = urllib.parse.quote_plus("Johncena@15")
DB_HOST = "localhost"
DB_NAME = "tdm_orchestrator_system"

connection_uri = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(connection_uri, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# --- DATABASE HELPER FUNCTIONS ---

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_request(request_id: int, db: Session):
    return db.query(RequestDB).filter(RequestDB.request_id == request_id).first()

def get_scenario(scenario_id: int, db: Session):
    return db.query(ScenarioDB).filter(ScenarioDB.scenario_id == scenario_id).first()

def get_tasks_for_scenario(scenario_id: int, db: Session):
    return db.query(TaskLogDB).filter(TaskLogDB.scenario_id == scenario_id).order_by(TaskLogDB.task_id).all()

def get_status_log(request_id: int, db: Session):
    return db.query(StatusLogDB).filter(StatusLogDB.request_id == request_id).order_by(StatusLogDB.task_id).all()

def update_request_status(request_id: int, status: str):
    with get_db() as db:
        request = get_request(request_id, db)
        if request:
            request.status = status
            db.commit()

def initialize_status_log(request_id: int, scenario_id: int):
    """Initialize status log for a new request"""
    with get_db() as db:
        # Get all tasks for the scenario
        tasks = get_tasks_for_scenario(scenario_id, db)
        
        # Clear any existing status log for this request
        db.query(StatusLogDB).filter(StatusLogDB.request_id == request_id).delete()
        
        # Create status log entries
        for i, task in enumerate(tasks):
            next_task_id = tasks[i + 1].task_id if i < len(tasks) - 1 else None
            prev_task_id = tasks[i - 1].task_id if i > 0 else None
            
            status_entry = StatusLogDB(
                request_id=request_id,
                scenario_id=scenario_id,
                task_id=task.task_id,
                task_desc=task.task_desc,
                status_of_task="PENDING",
                next_task=next_task_id,
                previous_task=prev_task_id
            )
            db.add(status_entry)
        
        db.commit()

def update_task_status(request_id: int, task_id: int, status: str):
    """Update the status of a specific task"""
    with get_db() as db:
        status_entry = db.query(StatusLogDB).filter(
            StatusLogDB.request_id == request_id,
            StatusLogDB.task_id == task_id
        ).first()
        
        if status_entry:
            status_entry.status_of_task = status
            status_entry.updated_at = func.now()
            db.commit()

def get_waiting_task(request_id: int, db: Session):
    """Get the task that is currently waiting"""
    return db.query(StatusLogDB).filter(
        StatusLogDB.request_id == request_id,
        StatusLogDB.status_of_task == "WAITING"
    ).first()

def get_pending_tasks(request_id: int, db: Session):
    """Get all pending tasks"""
    return db.query(StatusLogDB).filter(
        StatusLogDB.request_id == request_id,
        StatusLogDB.status_of_task == "PENDING"
    ).order_by(StatusLogDB.task_id).all()

def get_tasks_after_waiting(request_id: int, waiting_task_id: int, db: Session):
    """Get all tasks that come after the waiting task"""
    return db.query(StatusLogDB).filter(
        StatusLogDB.request_id == request_id,
        StatusLogDB.task_id > waiting_task_id,
        StatusLogDB.status_of_task == "PENDING"
    ).order_by(StatusLogDB.task_id).all()

# --- PYDANTIC MODELS ---

class OrchestratorState(TypedDict):
    request_id: int
    scenario_id: int
    messages: List[str]
    action: Optional[str]
    user_prompt: Optional[str]
    reasoning: Optional[str]

class WorkflowRequest(BaseModel):
    request_id: int
    scenario_id: int
    description: Optional[str] = None

# --- LLM SETUP ---

llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0,
    api_key="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",
)

parser = StrOutputParser()

# --- WAITING TASK AUTO-COMPLETION TRACKER ---
waiting_task_timers: Dict[int, asyncio.Task] = {}

async def auto_complete_waiting_task(request_id: int, task_id: int):
    """Automatically complete a waiting task after 50-70 seconds"""
    wait_time = random.randint(50, 70)
    print(f"[AutoComplete] ⏰ Task {task_id} will auto-complete in {wait_time} seconds")
    
    await asyncio.sleep(wait_time)
    
    # Mark task as completed
    update_task_status(request_id, task_id, "COMPLETED")
    print(f"[AutoComplete] ✅ Task {task_id} auto-completed after {wait_time} seconds")

# --- CDF AGENT CLASS ---

class CDFAgent:
    """CDF Agent that executes tasks based on orchestrator prompts"""
    
    def __init__(self, request_id: int):
        self.request_id = request_id
        self.agent_name = "CDF_Agent"
    
    def execute(self, user_prompt: str, action_type: str) -> str:
        """Execute tasks based on the user prompt from orchestrator"""
        
        print(f"\n{'='*80}")
        print(f"[CDF_Agent] 🤖 Executing action: {action_type}")
        print(f"[CDF_Agent] 📋 Prompt: {user_prompt}")
        print(f"{'='*80}\n")
        
        with get_db() as db:
            if action_type == "initial_call":
                return self._execute_initial_tasks(db)
            elif action_type == "waiting_task_call":
                return self._execute_waiting_task(user_prompt, db)
            elif action_type == "remaining_tasks_call":
                return self._execute_remaining_tasks(user_prompt, db)
        
        return "Unknown action type"
    
    def _execute_initial_tasks(self, db: Session) -> str:
        """Execute tasks until we hit a waiting task"""
        status_log = get_status_log(self.request_id, db)
        completed_tasks = []
        
        for task in status_log:
            if task.status_of_task == "PENDING":
                # Check if this is the ServiceNow task
                if "service now ticket" in task.task_desc.lower():
                    print(f"[CDF_Agent] ⏸️  Task {task.task_id}: {task.task_desc} - WAITING")
                    update_task_status(self.request_id, task.task_id, "WAITING")
                    completed_tasks.append(f"Task {task.task_id}: {task.task_desc} - WAITING (requires manual intervention)")
                    
                    # Start auto-completion timer
                    if self.request_id in waiting_task_timers:
                        waiting_task_timers[self.request_id].cancel()
                    waiting_task_timers[self.request_id] = asyncio.create_task(
                        auto_complete_waiting_task(self.request_id, task.task_id)
                    )
                    break
                else:
                    print(f"[CDF_Agent] ✅ Task {task.task_id}: {task.task_desc} - COMPLETED")
                    update_task_status(self.request_id, task.task_id, "COMPLETED")
                    completed_tasks.append(f"Task {task.task_id}: {task.task_desc} - COMPLETED")
        
        result = "\n".join(completed_tasks)
        print(f"\n[CDF_Agent] 📊 Initial execution complete")
        return result
    
    def _execute_waiting_task(self, user_prompt: str, db: Session) -> str:
        """Check if waiting task is completed"""
        waiting_task = get_waiting_task(self.request_id, db)
        
        if not waiting_task:
            print(f"[CDF_Agent] ✅ Waiting task already completed!")
            return "Waiting task already completed"
        
        print(f"[CDF_Agent] ⏳ Task {waiting_task.task_id} still waiting: {waiting_task.task_desc}")
        result = f"Task {waiting_task.task_id}: {waiting_task.task_desc} - STILL WAITING"
        return result
    
    def _execute_remaining_tasks(self, user_prompt: str, db: Session) -> str:
        """Execute all remaining tasks after the waiting task"""
        # Get all pending tasks
        pending_tasks = get_pending_tasks(self.request_id, db)
        
        if not pending_tasks:
            print(f"[CDF_Agent] ✅ No remaining tasks to execute")
            return "All tasks completed"
        
        completed_tasks = []
        
        for task in pending_tasks:
            print(f"[CDF_Agent] ✅ Task {task.task_id}: {task.task_desc} - COMPLETED")
            update_task_status(self.request_id, task.task_id, "COMPLETED")
            completed_tasks.append(f"Task {task.task_id}: {task.task_desc} - COMPLETED")
        
        result = "\n".join(completed_tasks) if completed_tasks else "No remaining tasks to execute"
        print(f"\n[CDF_Agent] 📊 All remaining tasks completed")
        return result

# --- BACKGROUND POLLING MANAGER ---

class PollingManager:
    """Manages background polling for waiting tasks"""
    def __init__(self):
        self.active_polls: Dict[int, bool] = {}
    
    async def start_polling(self, request_id: int):
        """Start polling for a request"""
        if request_id in self.active_polls:
            print(f"[PollingManager] ⚠️  Polling already active for request {request_id}")
            return
        
        self.active_polls[request_id] = True
        print(f"[PollingManager] 🔄 Starting polling for request {request_id}")
        
        asyncio.create_task(self._poll_loop(request_id))
    
    async def _poll_loop(self, request_id: int):
        poll_count = 0
        
        while self.active_polls.get(request_id, False):
            poll_count += 1
            print(f"\n[PollingManager] 🔍 Poll #{poll_count} - Re-triggering orchestrator for request {request_id}")
            
            try:
                with get_db() as db:
                    status_log = get_status_log(request_id, db)
                    all_completed = all(t.status_of_task == "COMPLETED" for t in status_log)
                    
                    if all_completed:
                        print(f"[PollingManager] 🎉 All tasks completed! Stopping polling.")
                        self.stop_polling(request_id)
                        break
                    
                    scenario_id = status_log[0].scenario_id if status_log else 0
                
                # Always re-trigger orchestrator every 30 seconds
                print(f"[PollingManager] 🔄 Re-triggering orchestrator (Poll #{poll_count})")
                
                config = {
                    "configurable": {"thread_id": str(request_id)},
                    "recursion_limit": 50
                }
                
                resume_input = {
                    "request_id": request_id,
                    "scenario_id": scenario_id,
                    "messages": [f"[POLLING] 🔄 Poll #{poll_count} - re-triggering orchestrator"],
                    "action": None,
                    "user_prompt": None,
                    "reasoning": None
                }
                
                step_count = 0
                for state in app_graph.stream(resume_input, config, stream_mode="values"):
                    step_count += 1
                    last_msg = state.get("messages", [])[-1] if state.get("messages") else "No message"
                    print(f"[PollingManager] Step {step_count}: {last_msg}")
                    
                    if step_count > 20:
                        print("[PollingManager] ⚠️ Too many steps, stopping this iteration")
                        break
                
                # Check if all tasks are completed now
                with get_db() as db2:
                    status_log2 = get_status_log(request_id, db2)
                    all_completed2 = all(t.status_of_task == "COMPLETED" for t in status_log2)
                    
                    if all_completed2:
                        print(f"[PollingManager] 🎉 All tasks completed! Stopping polling.")
                        self.stop_polling(request_id)
                        break
            
            except Exception as e:
                print(f"[PollingManager] ❌ Error during polling: {e}")
                import traceback
                traceback.print_exc()
            
            # Wait 30 seconds before next poll
            print(f"[PollingManager] ⏰ Waiting 30 seconds before next poll...")
            await asyncio.sleep(30)
        
        print(f"[PollingManager] 🛑 Polling stopped for request {request_id}")
    
    def stop_polling(self, request_id: int):
        """Stop polling for a request"""
        if request_id in self.active_polls:
            del self.active_polls[request_id]
            print(f"[PollingManager] 🛑 Stopped polling for request {request_id}")

# Global polling manager instance
polling_manager = PollingManager()

# --- WORKFLOW NODES ---

def orchestrator_llm_node(state: OrchestratorState) -> OrchestratorState:
    """TDM Orchestrator LLM that decides which action to take"""
    request_id = state["request_id"]
    scenario_id = state["scenario_id"]
    
    with get_db() as db:
        status_log = get_status_log(request_id, db)
        
        # Analyze current state
        waiting_task = get_waiting_task(request_id, db)
        pending_tasks = get_pending_tasks(request_id, db)
        
        total_tasks = len(status_log)
        completed_tasks = sum(1 for t in status_log if t.status_of_task == "COMPLETED")
        
        # Build status summary
        status_summary = []
        for task in status_log:
            status_summary.append(
                f"Task {task.task_id}: {task.task_desc} - {task.status_of_task}"
            )
        
        status_text = "\n".join(status_summary)
        
        context = f"""
You are the TDM Orchestrator Agent responsible for managing task execution workflows.

CURRENT STATE:
- Request ID: {request_id}
- Scenario ID: {scenario_id}
- Total Tasks: {total_tasks}
- Completed Tasks: {completed_tasks}
- Pending Tasks: {len(pending_tasks)}
- Waiting Task: {'Yes - Task ' + str(waiting_task.task_id) if waiting_task else 'No'}

TASK STATUS:
{status_text}

AVAILABLE ACTIONS:
1. "initial_call" - Start executing tasks from the beginning (use when all tasks are PENDING)
2. "waiting_task_call" - Check the specific waiting task status (use when a task status is WAITING)
3. "remaining_tasks_call" - Execute all tasks after the waiting task (use when waiting task is COMPLETED and there are PENDING tasks)

DECISION RULES:
- If all tasks are PENDING and no waiting task: choose "initial_call"
  → Generate user prompt: "Execute CDF Refresh tasks starting from task 1"
  
- If there is a WAITING task: choose "waiting_task_call"
  → Generate user prompt with the waiting task description: "Check status of [task_desc]"
  
- If no waiting task but there are PENDING tasks (meaning waiting task was completed): choose "remaining_tasks_call"
  → Generate user prompt: "Execute remaining CDF Refresh tasks: [list of remaining task descriptions]"

Respond with ONLY a JSON object:
{{
    "action": "one of: initial_call, waiting_task_call, remaining_tasks_call",
    "user_prompt": "the specific prompt to send to CDF Agent",
    "reasoning": "brief explanation of why this action was chosen"
}}

No markdown formatting.
"""

        orchestrator_prompt = ChatPromptTemplate.from_template("{context}")
        chain = orchestrator_prompt | llm | parser
        
        print(f"[Orchestrator] 🤔 Deciding next action...")
        
        llm_response = chain.invoke({"context": context})
        
        try:
            json_match = re.search(r"\{.*\}", llm_response, re.DOTALL)
            if not json_match:
                raise ValueError("LLM did not return valid JSON")
            
            decision = json.loads(json_match.group())
            action = decision.get("action", "initial_call")
            user_prompt = decision.get("user_prompt", "Execute tasks")
            reasoning = decision.get("reasoning", "No reasoning provided")
            
            print(f"[Orchestrator] ✅ Decision: {action}")
            print(f"[Orchestrator] 📝 User Prompt: {user_prompt}")
            print(f"[Orchestrator] 💭 Reasoning: {reasoning}")
            
            state["action"] = action
            state["user_prompt"] = user_prompt
            state["reasoning"] = reasoning
            
            msg = f"[ORCHESTRATOR] 🎯 Action: {action} | Prompt: {user_prompt}"
            state["messages"].append(msg)
            
        except Exception as e:
            print(f"[Orchestrator] ❌ Error: {e}")
            state["action"] = "error"
            state["user_prompt"] = ""
            state["reasoning"] = f"Error: {str(e)}"
    
    return state

def cdf_agent_node(state: OrchestratorState) -> OrchestratorState:
    """CDF Agent node that executes tasks"""
    request_id = state["request_id"]
    action = state.get("action", "initial_call")
    user_prompt = state.get("user_prompt", "")
    
    # Create agent instance
    agent = CDFAgent(request_id)
    
    # Execute based on action
    result = agent.execute(user_prompt, action)
    
    msg = f"[CDF_AGENT] ✅ {result}"
    state["messages"].append(msg)
    
    return state

# --- ROUTING FUNCTIONS ---

def route_from_orchestrator(state: OrchestratorState) -> str:
    """Route based on orchestrator's decision"""
    action = state.get("action", "error")
    request_id = state["request_id"]
    
    # Check if all tasks are completed
    with get_db() as db:
        status_log = get_status_log(request_id, db)
        all_completed = all(t.status_of_task == "COMPLETED" for t in status_log)
    
    if all_completed:
        print(f"[Route] 🎉 All tasks completed! Workflow ending.")
        update_request_status(request_id, "COMPLETED")
        polling_manager.stop_polling(request_id)
        return "end"
    
    # Go to CDF agent
    print(f"[Route] 🔀 Action '{action}' -> cdf_agent")
    return "cdf_agent"

def route_from_cdf_agent(state: OrchestratorState) -> str:
    """Route after CDF agent execution"""
    request_id = state["request_id"]
    action = state.get("action", "")
    
    with get_db() as db:
        waiting_task = get_waiting_task(request_id, db)
        status_log = get_status_log(request_id, db)
        all_completed = all(t.status_of_task == "COMPLETED" for t in status_log)
    
    if all_completed:
        print(f"[Route] 🎉 All tasks completed after CDF agent!")
        update_request_status(request_id, "COMPLETED")
        polling_manager.stop_polling(request_id)
        return "end"
    
    if waiting_task:
        print(f"[Route] ⏸️  Waiting task detected, pausing workflow for polling")
        return "end"
    
    # Continue to orchestrator for next decision
    print(f"[Route] 🔄 Returning to orchestrator for next action")
    return "orchestrator"

# --- LANGGRAPH WORKFLOW ---

memory = MemorySaver()

workflow = StateGraph(OrchestratorState)

# Add nodes
workflow.add_node("orchestrator", orchestrator_llm_node)
workflow.add_node("cdf_agent", cdf_agent_node)

# Set entry point
workflow.set_entry_point("orchestrator")

# Orchestrator routes to CDF agent or end
workflow.add_conditional_edges(
    "orchestrator",
    route_from_orchestrator,
    {
        "cdf_agent": "cdf_agent",
        "end": END
    }
)

# CDF agent routes back to orchestrator or end
workflow.add_conditional_edges(
    "cdf_agent",
    route_from_cdf_agent,
    {
        "orchestrator": "orchestrator",
        "end": END
    }
)

# Compile with checkpointing
app_graph = workflow.compile(checkpointer=memory)

# --- FASTAPI APP ---

app = FastAPI(
    title="TDM Orchestrator Workflow API",
    description="Orchestrator-driven task execution workflow",
    version="2.0.0"
)

@app.post("/execute-workflow", tags=["Workflow"])
async def execute_workflow(request: WorkflowRequest):
    """Start the orchestrated workflow for a request"""
    
    with get_db() as db:
        # Validate request exists
        req = get_request(request.request_id, db)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Validate scenario exists
        scenario = get_scenario(request.scenario_id, db)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Check if status log already exists
        existing_status = get_status_log(request.request_id, db)
        if not existing_status:
            # Initialize status log
            initialize_status_log(request.request_id, request.scenario_id)
            update_request_status(request.request_id, "IN_PROGRESS")
    
    config = {
        "configurable": {"thread_id": str(request.request_id)},
        "recursion_limit": 50
    }
    
    try:
        initial_state = {
            "request_id": request.request_id,
            "scenario_id": request.scenario_id,
            "messages": [f"[WORKFLOW] Starting orchestration for request {request.request_id}"],
            "action": None,
            "user_prompt": None,
            "reasoning": None
        }
        
        print(f"\n{'='*80}")
        print(f"[Workflow] 🚀 Starting orchestration for request {request.request_id}")
        print(f"{'='*80}\n")
        
        # Start polling immediately
        asyncio.create_task(polling_manager.start_polling(request.request_id))
        
        final_state = None
        step_count = 0
        
        for state in app_graph.stream(initial_state, config, stream_mode="values"):
            final_state = state
            step_count += 1
            last_msg = state.get("messages", [])[-1] if state.get("messages") else "No message"
            print(f"[Workflow] Step {step_count}: {last_msg}")
            
            if step_count > 30:
                print("[Workflow] ⚠️ Too many steps, stopping")
                break
        
        # Check current status
        with get_db() as db:
            waiting_task = get_waiting_task(request.request_id, db)
            status_log = get_status_log(request.request_id, db)
            all_completed = all(t.status_of_task == "COMPLETED" for t in status_log)
        
        if all_completed:
            print(f"[Workflow] 🎉 All tasks completed!")
            update_request_status(request.request_id, "COMPLETED")
            polling_manager.stop_polling(request.request_id)
            
            return {
                "status": "COMPLETED",
                "message": "All tasks completed successfully",
                "workflow_messages": final_state.get("messages", []) if final_state else []
            }
        elif waiting_task:
            print(f"[Workflow] ⏸️  Workflow paused - waiting for task {waiting_task.task_id}")
            update_request_status(request.request_id, "WAITING")
            
            return {
                "status": "WAITING",
                "message": f"Workflow paused - waiting for task {waiting_task.task_id}: {waiting_task.task_desc}",
                "waiting_task": {
                    "task_id": waiting_task.task_id,
                    "task_desc": waiting_task.task_desc
                },
                "workflow_messages": final_state.get("messages", []) if final_state else [],
                "polling_active": True,
                "note": "🤖 Polling active - checking every 30 seconds. Task will auto-complete in 50-70 seconds."
            }
        else:
            return {
                "status": "IN_PROGRESS",
                "message": "Workflow in progress",
                "workflow_messages": final_state.get("messages", []) if final_state else [],
                "polling_active": request.request_id in polling_manager.active_polls
            }
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        update_request_status(request.request_id, "FAILED")
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")

@app.get("/workflow-status/{request_id}", tags=["Status"])
def get_workflow_status(request_id: int):
    """Get the current status of a workflow"""
    
    with get_db() as db:
        request = get_request(request_id, db)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        status_log = get_status_log(request_id, db)
        if not status_log:
            raise HTTPException(status_code=404, detail="Workflow not started")
        
        waiting_task = get_waiting_task(request_id, db)
        
        completed_count = sum(1 for t in status_log if t.status_of_task == "COMPLETED")
        pending_count = sum(1 for t in status_log if t.status_of_task == "PENDING")
        waiting_count = sum(1 for t in status_log if t.status_of_task == "WAITING")
        
        return {
            "request_id": request_id,
            "status": request.status,
            "total_tasks": len(status_log),
            "completed_tasks": completed_count,
            "pending_tasks": pending_count,
            "waiting_tasks": waiting_count,
            "waiting_task": {
                "task_id": waiting_task.task_id,
                "task_desc": waiting_task.task_desc
            } if waiting_task else None,
            "polling_active": request_id in polling_manager.active_polls,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "task_desc": t.task_desc,
                    "status": t.status_of_task,
                    "next_task": t.next_task,
                    "previous_task": t.previous_task
                } for t in status_log
            ]
        }

@app.get("/health", tags=["System"])
def health_check():
    """Health check"""
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "active_polls": len(polling_manager.active_polls),
            "version": "2.0.0"
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
        "name": "TDM Orchestrator Workflow API",
        "version": "2.0.0",
        "description": "Orchestrator-driven task execution workflow with LLM decision making",
        "features": [
            "🤖 LLM orchestrator makes all decisions",
            "⏰ Waiting tasks auto-complete in 50-70 seconds",
            "🔄 Auto-polling every 30 seconds",
            "📊 Three orchestrator actions: initial_call, waiting_task_call, remaining_tasks_call"
        ],
        "workflow": [
            "1️⃣ Orchestrator LLM analyzes task status",
            "2️⃣ Decides: initial_call, waiting_task_call, or remaining_tasks_call",
            "3️⃣ CDF Agent executes tasks based on orchestrator prompt",
            "4️⃣ Polling runs every 30 seconds checking for completion",
            "5️⃣ Waiting task auto-completes in 50-70 seconds",
            "6️⃣ Workflow resumes automatically when waiting task completes"
        ],
        "key_endpoints": {
            "start_workflow": "POST /execute-workflow",
            "get_status": "GET /workflow-status/{request_id}"
        },
        "quick_start": [
            "1. Ensure setup_database.py is running and data is initialized",
            "2. Create a request using setup API",
            "3. POST /execute-workflow with request_id and scenario_id",
            "4. Polling starts automatically",
            "5. Waiting task auto-completes in 50-70 seconds",
            "6. Workflow resumes automatically"
        ],
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("LO2:app", host="0.0.0.0", port=8000, reload=True)