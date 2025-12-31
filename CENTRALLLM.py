from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import re
import urllib.parse
import asyncio
from sqlalchemy import create_engine, Column, String, Text, Integer, TIMESTAMP, JSON as SQLJSON, ForeignKey, Boolean
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
DB_PASSWORD = urllib.parse.quote_plus("******")
DB_HOST = "localhost"
DB_NAME = "medical_discharge_system"

connection_uri = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(connection_uri, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODELS ---

class ConsultationDB(Base):
    __tablename__ = "consultations"
    
    consultation_id = Column(String(100), primary_key=True)
    patient_id = Column(String(100), nullable=False)
    doctor_id = Column(String(100), nullable=False)
    specialty = Column(String(100), default="General")
    raw_transcript = Column(Text)
    cleaned_transcript = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class DischargeSummaryDB(Base):
    __tablename__ = "discharge_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(String(100), ForeignKey('consultations.consultation_id'), unique=True, nullable=False)
    history = Column(SQLJSON)
    diagnosis = Column(SQLJSON)
    exam_findings = Column(Text)
    followup_instructions = Column(Text)
    final_status = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class MedicationDB(Base):
    __tablename__ = "medications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(String(100), ForeignKey('consultations.consultation_id'), nullable=False)
    name = Column(String(200), nullable=False)
    dose = Column(String(100))
    frequency = Column(String(100))
    created_at = Column(TIMESTAMP, server_default=func.now())

class WorkflowStatusDB(Base):
    __tablename__ = "workflow_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(String(100), ForeignKey('consultations.consultation_id'), nullable=False)
    status = Column(String(50), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())

class WorkflowLogDB(Base):
    __tablename__ = "workflow_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(String(100), ForeignKey('consultations.consultation_id'), nullable=False)
    message = Column(Text, nullable=False)
    log_type = Column(String(50))
    timestamp = Column(TIMESTAMP, server_default=func.now())

class HumanInterventionDB(Base):
    __tablename__ = "human_interventions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(String(100), ForeignKey('consultations.consultation_id'), nullable=False)
    intervention_type = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    missing_fields = Column(SQLJSON)
    status = Column(String(50), default="PENDING")
    polling_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    resolved_at = Column(TIMESTAMP, nullable=True)

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

def update_status(consultation_id: str, state: str):
    with get_db() as db:
        status_entry = WorkflowStatusDB(consultation_id=consultation_id, status=state)
        db.add(status_entry)
        db.commit()

def log_workflow_message(consultation_id: str, message: str, log_type: str = "INFO"):
    with get_db() as db:
        log_entry = WorkflowLogDB(
            consultation_id=consultation_id,
            message=message,
            log_type=log_type
        )
        db.add(log_entry)
        db.commit()

def create_human_intervention(consultation_id: str, intervention_type: str, reason: str, missing_fields: List[str]):
    with get_db() as db:
        intervention = HumanInterventionDB(
            consultation_id=consultation_id,
            intervention_type=intervention_type,
            reason=reason,
            missing_fields=missing_fields,
            status="PENDING",
            polling_active=True
        )
        db.add(intervention)
        db.commit()
        return intervention.id

def resolve_human_intervention(consultation_id: str):
    with get_db() as db:
        interventions = db.query(HumanInterventionDB).filter(
            HumanInterventionDB.consultation_id == consultation_id,
            HumanInterventionDB.status == "PENDING"
        ).all()
        
        for intervention in interventions:
            intervention.status = "RESOLVED"
            intervention.polling_active = False
            intervention.resolved_at = func.now()
        
        db.commit()

def get_pending_interventions(consultation_id: str):
    with get_db() as db:
        return db.query(HumanInterventionDB).filter(
            HumanInterventionDB.consultation_id == consultation_id,
            HumanInterventionDB.status == "RESOLVED"
        ).all()

def get_consultation(consultation_id: str, db: Session):
    return db.query(ConsultationDB).filter(ConsultationDB.consultation_id == consultation_id).first()

def get_discharge_summary(consultation_id: str, db: Session):
    return db.query(DischargeSummaryDB).filter(DischargeSummaryDB.consultation_id == consultation_id).first()

def get_medications(consultation_id: str, db: Session):
    return db.query(MedicationDB).filter(MedicationDB.consultation_id == consultation_id).all()

# --- PYDANTIC MODELS ---

class Medication(BaseModel):
    name: str
    dose: str
    frequency: str

class ConsultationData(BaseModel):
    consultation_id: str
    patient_id: str
    doctor_id: str
    specialty: str
    raw_transcript: Optional[str] = ""
    cleaned_transcript: Optional[str] = None

class DischargeData(BaseModel):
    consultation_id: str
    history: Optional[List[str]] = None
    diagnosis: Optional[List[str]] = None
    exam_findings: Optional[str] = None
    medications: Optional[List[Medication]] = None
    followup_instructions: Optional[str] = None
    final_status: Optional[str] = None

class OrchestratorState(TypedDict):
    consultation_id: str
    messages: List[str]
    next_action: Optional[str]
    reasoning: Optional[str]
    completed_actions: Optional[List[str]]

# --- LLM SETUP ---

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key="********",
)

parser = StrOutputParser()

# --- BACKGROUND POLLING MANAGER ---

class PollingManager:
    """Manages background polling for pending interventions"""
    def __init__(self):
        self.active_polls: Dict[str, bool] = {}
    
    async def start_polling(self, consultation_id: str):
        """Start polling for a consultation"""
        if consultation_id in self.active_polls:
            print(f"[PollingManager] ⚠️  Polling already active for {consultation_id}")
            return
        
        self.active_polls[consultation_id] = True
        print(f"[PollingManager] 🔄 Starting autonomous polling for {consultation_id}")
        
        asyncio.create_task(self._poll_loop(consultation_id))
    '''
    async def _poll_loop(self, consultation_id: str):
        """Background polling loop"""
        poll_count = 0
        
        while self.active_polls.get(consultation_id, False):
            poll_count += 1
            print(f"\n[PollingManager] 🔍 Poll #{poll_count} for {consultation_id}")
            
            try:
                # Check if transcript is now available
                with get_db() as db:
                    consultation = get_consultation(consultation_id, db)
                    has_transcript = bool(
                        consultation and 
                        consultation.raw_transcript and 
                        len(consultation.raw_transcript.strip()) >= 50
                    )
                
               
                if has_transcript:
                    print(f"[PollingManager] 🎉 Transcript now available! Resuming workflow for {consultation_id}")
                    
                    # Resolve interventions
                    resolve_human_intervention(consultation_id)
                    
                    # Resume workflow
                    await self._resume_workflow(consultation_id)
                    
                    self.stop_polling(consultation_id)
                    break
                else:
                    print(f"[PollingManager] ⏳ Still waiting for transcript...")
                    log_workflow_message(
                        consultation_id,
                        f"[POLLING] Still waiting for transcript",
                        "POLLING"
                    )
                
            except Exception as e:
                print(f"[PollingManager] ❌ Error during poll: {e}")
                log_workflow_message(consultation_id, f"[POLLING ERROR] {str(e)}", "ERROR")
            
            # Wait 30 seconds before next poll
            await asyncio.sleep(30)
        
        print(f"[PollingManager] 🛑 Polling stopped for {consultation_id}")
        '''
    async def _poll_loop(self, consultation_id: str):
        poll_count = 0

        while self.active_polls.get(consultation_id, False):
            poll_count += 1
            print(
                f"\n[PollingManager] 🔁 Poll #{poll_count} — "
                f"re-triggering orchestrator for {consultation_id}"
            )

            try:
                config = {
                    "configurable": {"thread_id": consultation_id},
                    "recursion_limit": 50
                }

                # 🔥 Restart execution from the orchestrator entry point
                orchestrator_input = {
                    "consultation_id": consultation_id,
                    "messages": [
                        f"[POLLING] 🔄 Re-checking transcript availability "
                        f"(poll #{poll_count})"
                    ],
                    "next_action": None,
                    "reasoning": None,
                    "completed_actions": []
                }

                final_state = None
                step_count = 0

                for state in app_graph.stream(
                    orchestrator_input,
                    config,
                    stream_mode="values"
                ):
                    final_state = state
                    step_count += 1

                    last_msg = (
                        state.get("messages", [])[-1]
                        if state.get("messages")
                        else "No message"
                    )

                    print(f"[PollingManager] Step {step_count}: {last_msg}")

                    # Safety guard to prevent infinite loops
                    if step_count > 30:
                        print(
                            "[PollingManager] ⚠️ Too many steps, "
                            "stopping this polling iteration"
                        )
                        break

                # 🔎 Check if workflow is still waiting for human input
                resolved = get_pending_interventions(consultation_id)
                if resolved:
                    print(
                        f"[PollingManager] ✅ Workflow resumed successfully "
                        f"for {consultation_id}"
                    )
                    log_workflow_message(
                        consultation_id,
                        "[POLLING] Workflow resumed successfully, stopping polling",
                        "POLLING"
                    )

                    self.stop_polling(consultation_id)
                    break
                else:
                    print(
                        f"[PollingManager] ⏳ Still waiting for transcript "
                        f"for {consultation_id}"
                    )

            except Exception as e:
                print(
                    f"[PollingManager] ❌ Error during polling iteration: {e}"
                )
                log_workflow_message(
                    consultation_id,
                    f"[POLLING ERROR] {str(e)}",
                    "ERROR"
                )

            # ⏱️ Wait 30 seconds before next poll
            await asyncio.sleep(30)

        print(f"[PollingManager] 🛑 Polling stopped for {consultation_id}")


    async def _resume_workflow(self, consultation_id: str):
        """Resume the workflow after intervention is resolved"""
        try:
            config = {
                "configurable": {"thread_id": consultation_id},
                "recursion_limit": 50
            }
            
            log_workflow_message(
                consultation_id,
                "[AUTONOMOUS RESUME] Transcript received, resuming workflow",
                "RESUME"
            )
            
            print(f"[PollingManager] 📍 Resuming workflow for {consultation_id}")
            
            # CRITICAL FIX: We must pass an input to start a NEW run from the entry point.
            # Passing None would just check the 'END' state and stop again.
            resume_input = {
                "messages": ["[SYSTEM] 🔄 Transcript detected by background poller. Resuming workflow."]
            }
            
            # Continue the workflow - this starts from the Entry Point (Orchestrator)
            final_state = None
            step_count = 0
            
            # We pass 'resume_input' instead of 'None'
            for state in app_graph.stream(resume_input, config, stream_mode="values"):
                final_state = state
                step_count += 1
                last_msg = state.get('messages', [])[-1] if state.get('messages') else 'No message'
                print(f"[PollingManager] Step {step_count}: {last_msg}")
                
                # Safety check
                if step_count > 20:
                    print(f"[PollingManager] ⚠️ Too many steps, stopping")
                    break
            
            print(f"[PollingManager] ✅ Workflow completed in {step_count} steps for {consultation_id}")
            
        except Exception as e:
            print(f"[PollingManager] ❌ Error resuming workflow: {e}")
            import traceback
            traceback.print_exc()
            log_workflow_message(consultation_id, f"[RESUME ERROR] {str(e)}", "ERROR")
    def stop_polling(self, consultation_id: str):
        """Stop polling for a consultation"""
        if consultation_id in self.active_polls:
            self.active_polls[consultation_id] = False
            print(f"[PollingManager] 🛑 Stopped polling for {consultation_id}")

# Global polling manager instance
polling_manager = PollingManager()

# --- WORKFLOW STEP FUNCTIONS ---
def _normalize_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    if isinstance(value, list):
        out = []
        for v in value:
            if v is None:
                continue
            s = str(v).strip()
            if s:
                out.append(s)
        return out
    s = str(value).strip()
    return [s] if s else []

def step_cleanup(state: OrchestratorState) -> OrchestratorState:
    """Clean up the transcript"""
    c_id = state["consultation_id"]
    
    with get_db() as db:
        consultation = get_consultation(c_id, db)
        if consultation:
            consultation.cleaned_transcript = (consultation.raw_transcript or "").strip()
            db.commit()
            
    update_status(c_id, "CLEANED")
    msg = "[CLEANUP] ✅ Transcript cleaned"
    state["messages"].append(msg)
    log_workflow_message(c_id, msg, "STEP")
    
    # Mark as completed
    completed = state.get("completed_actions", [])
    if "cleanup" not in completed:
        state["completed_actions"] = completed + ["cleanup"]
    
    return state

def step_summarize(state: OrchestratorState) -> OrchestratorState:
    """Extract medical information from transcript"""
    c_id = state["consultation_id"]
    
    with get_db() as db:
        consultation = get_consultation(c_id, db)

        if not consultation.cleaned_transcript or not consultation.cleaned_transcript.strip():
            print(f"[step_summarize] ❌ Transcript missing for {c_id}, skipping generation")
            return state
        
        prompt = ChatPromptTemplate.from_template(
            """
            You are a medical discharge summary assistant.

            From the following cleaned transcript, produce a SINGLE STRICT JSON object
            with ALL of these fields:

            - chief_complaint: string
            - history: array of strings (each item can be a sentence)
            - exam_findings: string
            - diagnosis: array of strings
            - investigations: array of strings (or empty array if none)
            - medications: array of objects with keys: name, dose, frequency
            - follow_up_instructions: string

            Rules:
            - DO NOT leave any field empty.
            - If something is not explicitly stated, infer a reasonable, concise entry,
              or write "Not clearly specified in the transcript".
            - Return STRICT VALID JSON ONLY. No markdown, no comments, no extra text.

            Transcript:
            {transcript}
            """
        )

        chain = prompt | llm | parser
        llm_output = chain.invoke({"transcript": consultation.cleaned_transcript})

        json_str = re.search(r"\{.*\}", llm_output, re.DOTALL)
        if not json_str:
            raise ValueError("LLM did not return JSON.")
        summary = json.loads(json_str.group())

        discharge_summary = get_discharge_summary(c_id, db)
        if not discharge_summary:
            discharge_summary = DischargeSummaryDB(consultation_id=c_id)
            db.add(discharge_summary)

        history = _normalize_str_list(summary.get("history"))
        diagnosis = _normalize_str_list(summary.get("diagnosis"))

        if not history:
            history = ["Not clearly specified in the transcript."]
        if not diagnosis:
            diagnosis = ["Not clearly specified in the transcript."]

        discharge_summary.history = history
        discharge_summary.diagnosis = diagnosis
        discharge_summary.exam_findings = summary.get("exam_findings", "Not clearly documented.")
        discharge_summary.followup_instructions = summary.get("follow_up_instructions") or summary.get("followup_instructions") or "No specific follow-up instructions documented."
        discharge_summary.final_status = "SUMMARY_GENERATED"

        db.query(MedicationDB).filter(MedicationDB.consultation_id == c_id).delete()
        
        meds_raw = summary.get("medications", [])
        if isinstance(meds_raw, list):
            for m in meds_raw:
                if isinstance(m, dict):
                    med = MedicationDB(
                        consultation_id=c_id,
                        name=(m.get("name") or "Not specified").strip(),
                        dose=(m.get("dose") or "Not specified").strip(),
                        frequency=(m.get("frequency") or "Not specified").strip()
                    )
                    db.add(med)

        db.commit()

    update_status(c_id, "SUMMARY_GENERATED")
    msg = "[SUMMARIZE] ✅ Medical information extracted"
    state["messages"].append(msg)
    log_workflow_message(c_id, msg, "STEP")
    
    # Mark as completed
    completed = state.get("completed_actions", [])
    if "summarize" not in completed:
        state["completed_actions"] = completed + ["summarize"]
    
    return state

def step_validate(state: OrchestratorState) -> OrchestratorState:
    """Validate the discharge summary"""
    c_id = state["consultation_id"]
    
    with get_db() as db:
        discharge = get_discharge_summary(c_id, db)
        medications = get_medications(c_id, db)
        
        validation_results = {
            "has_history": bool(discharge and discharge.history and len(discharge.history) > 0),
            "has_diagnosis": bool(discharge and discharge.diagnosis and len(discharge.diagnosis) > 0),
            "has_exam_findings": bool(discharge and discharge.exam_findings and discharge.exam_findings.strip()),
            "has_medications": bool(medications and len(medications) > 0),
            "has_followup": bool(discharge and discharge.followup_instructions and discharge.followup_instructions.strip())
        }
        
        all_valid = all(validation_results.values())
        
        if all_valid:
            msg = "[VALIDATE] ✅ All required fields are present"
            update_status(c_id, "VALIDATED")
        else:
            missing = [k for k, v in validation_results.items() if not v]
            msg = f"[VALIDATE] ⚠️ Missing fields: {', '.join(missing)}"
            update_status(c_id, "VALIDATION_FAILED")
        
        state["messages"].append(msg)
        log_workflow_message(c_id, msg, "STEP")
    
    # Mark as completed
    completed = state.get("completed_actions", [])
    if "validate" not in completed:
        state["completed_actions"] = completed + ["validate"]
    
    return state

def step_notify(state: OrchestratorState) -> OrchestratorState:
    """Notify doctor"""
    c_id = state["consultation_id"]
    update_status(c_id, "NOTIFIED_DOCTOR")
    msg = f"[NOTIFY] ✅ Doctor notified for {c_id}"
    state["messages"].append(msg)
    log_workflow_message(c_id, msg, "STEP")
    
    # Mark as completed
    completed = state.get("completed_actions", [])
    if "notify" not in completed:
        state["completed_actions"] = completed + ["notify"]
    
    return state

def step_error_handling(state: OrchestratorState) -> OrchestratorState:
    """Handle errors"""
    c_id = state["consultation_id"]
    update_status(c_id, "ERROR_HANDLED")
    msg = "[ERROR] ⚠️ Issues logged and escalated"
    state["messages"].append(msg)
    log_workflow_message(c_id, msg, "ERROR")
    return state

def wait_for_human_node(state: OrchestratorState) -> OrchestratorState:
    """Wait for human to provide transcript - triggers polling"""
    c_id = state["consultation_id"]
    
    msg = "[WAITING] 🔄 Waiting for transcript - polling every 30s"
    state["messages"].append(msg)
    log_workflow_message(c_id, msg, "INTERVENTION")
    
    # Create intervention record
    create_human_intervention(
        c_id,
        "MISSING_TRANSCRIPT",
        "Raw transcript is missing or too short",
        ["raw_transcript"]
    )
    
    # Start autonomous polling
    asyncio.create_task(polling_manager.start_polling(c_id))
    
    print(f"\n{'='*80}")
    print(f"⏸️  WAITING FOR HUMAN INPUT: {c_id}")
    print(f"Missing: Raw transcript")
    print(f"🤖 System will check every 30 seconds")
    print(f"{'='*80}\n")
    
    return state
def finish_pool_node(state: OrchestratorState) ->OrchestratorState:
    c_id = state["consultation_id"]
    completed = state.get("completed_actions", [])
    
    resolve_human_intervention(c_id)
    
    if "call_resolve_human _intervention" not in completed:
        state["completed_actions"] = completed + ["call_resolve_human _intervention"]
    return state

# --- CENTRAL LLM ORCHESTRATOR ---

def llm_orchestrator(state: OrchestratorState) -> OrchestratorState:
    """Central LLM orchestrator that decides ALL next actions"""
    c_id = state["consultation_id"]
    completed = state.get("completed_actions", [])
    if completed is None:
        completed = []
    
    with get_db() as db:
        consultation = get_consultation(c_id, db)
        discharge = get_discharge_summary(c_id, db)
        medications = get_medications(c_id, db)
        
        latest_status = db.query(WorkflowStatusDB).filter(
            WorkflowStatusDB.consultation_id == c_id
        ).order_by(WorkflowStatusDB.timestamp.desc()).first()
        
        current_status = latest_status.status if latest_status else "UNKNOWN"
        
        # Check transcript availability
        has_transcript = bool(
            consultation and 
            consultation.raw_transcript and 
            len(consultation.raw_transcript.strip()) >= 50
        )
        
        has_cleaned = bool(consultation and consultation.cleaned_transcript)
        has_summary = bool(discharge and discharge.history and discharge.diagnosis)
        
        # Build context for LLM
        recent_messages = state["messages"][-10:]
        clean_messages = " | ".join(recent_messages)
        
        context = f"""
You are the CENTRAL orchestrator for a medical discharge summary workflow.

CURRENT STATE:
- Consultation ID: {c_id}
- Current Status: {current_status}
- Has Raw Transcript: {has_transcript} ({len(consultation.raw_transcript) if consultation and consultation.raw_transcript else 0} chars)
- Has Cleaned Transcript: {has_cleaned}
- Discharge Summary Exists: {has_summary}
- Completed Actions: {', '.join(completed) if completed else 'None'}

DISCHARGE SUMMARY DETAILS:
- History Items: {len(discharge.history) if discharge and discharge.history else 0}
- Diagnosis Items: {len(discharge.diagnosis) if discharge and discharge.diagnosis else 0}
- Exam Findings: {'Present' if discharge and discharge.exam_findings else 'Missing'}
- Medications: {len(medications) if medications else 0}
- Follow-up: {'Present' if discharge and discharge.followup_instructions else 'Missing'}

WORKFLOW HISTORY: {clean_messages}

AVAILABLE ACTIONS:
1. "check_transcript" - To check if the transcript is present or not (not available anymore)
2. "wait_for_transcript" - Transcript is missing, need to wait for human to provide it
3. "cleanup" - Clean the raw transcript (requires raw transcript)
4. "summarize" - Extract medical info from transcript (requires cleaned transcript)
5. "validate" - Validate the discharge summary (requires summary)
6. "notify" - Notify doctor (final step after validation)
7. "complete" - All steps done, workflow complete
8. "error" - Something went wrong
9. "call_resolve_human_intervention"- To stop the polling process after the workflow is complete

DECISION RULES:
- If NO raw transcript (< 50 chars): choose "wait_for_transcript"
- If the raw transcript is obtained ,before cleanup call the resolve human intervention function and also choose this only one and after that bypass it to the next action : choose "call_resolve_human_intervention"
- If raw transcript exists and after call_resolve_human_intervention but NOT cleaned: choose "cleanup"
- If cleaned but NO summary: choose "summarize"
- If summary exists but NOT validated: choose "validate"
- If validated but NOT notified: choose "notify"
- If all done: choose "complete"
- DO NOT repeat completed actions

Respond with ONLY a JSON object:
{{
    "action": "one of the actions above",
    "reasoning": "brief explanation"
}}

No markdown formatting.
"""

        orchestrator_prompt = ChatPromptTemplate.from_template("{context}")
        chain = orchestrator_prompt | llm | parser
        
        print(f"[llm_orchestrator] 🤔 Asking LLM to decide next action...")
        print(f"[llm_orchestrator] 📋 Completed: {completed}")
        
        llm_response = chain.invoke({"context": context})
        
        try:
            json_match = re.search(r"\{.*\}", llm_response, re.DOTALL)
            if not json_match:
                raise ValueError("LLM did not return valid JSON")
            
            decision = json.loads(json_match.group())
            action = decision.get("action", "complete")
            reasoning = decision.get("reasoning", "No reasoning provided")
            
            # Prevent repeating actions
            if action in completed and action not in ["complete", "error", "wait_for_transcript"]:
                print(f"[llm_orchestrator] ⚠️ Action '{action}' already completed, marking as complete")
                action = "complete"
                reasoning = f"Action '{action}' was already done"
            
            print(f"[llm_orchestrator] ✅ Decision: {action}")
            print(f"[llm_orchestrator] 💭 Reasoning: {reasoning}")
            
            state["next_action"] = action
            state["reasoning"] = reasoning
            
            msg = f"[ORCHESTRATOR] 🎯 Next: {action} | {reasoning}"
            state["messages"].append(msg)
            log_workflow_message(c_id, msg, "DECISION")
            
        except Exception as e:
            print(f"[llm_orchestrator] ❌ Error: {e}")
            state["next_action"] = "error"
            state["reasoning"] = f"Error in orchestration: {str(e)}"
    
    return state

# --- ROUTING FUNCTIONS ---


def route_from_orchestrator(state: OrchestratorState) -> str:
    """Route based on orchestrator's decision"""
    action = state.get("next_action", "error")
    
    routing_map = {
        "wait_for_transcript": "wait_for_human",
        "call_resolve_human_intervention": "call_resolve_human_intervention",
        "cleanup": "cleanup",
        "summarize": "summarize",
        "validate": "validate",
        "notify": "notify",
        "error": "error_handling",
        "complete": "end"
    }
    
    next_node = routing_map.get(action, "error_handling")
    print(f"[route] 🔀 Orchestrator decided: {action} -> {next_node}")
    return next_node

# --- LANGGRAPH WORKFLOW ---

memory = MemorySaver()

workflow = StateGraph(OrchestratorState)

# Add all nodes
#workflow.add_node("check_transcript", check_transcript_node)
workflow.add_node("orchestrator", llm_orchestrator)
workflow.add_node("wait_for_human", wait_for_human_node)
workflow.add_node("cleanup", step_cleanup)
workflow.add_node("summarize", step_summarize)
workflow.add_node("validate", step_validate)
workflow.add_node("notify", step_notify)
workflow.add_node("error_handling", step_error_handling)
workflow.add_node("call_resolve_human_intervention", finish_pool_node)
# Set entry point
#workflow.set_entry_point("check_transcript")
workflow.set_entry_point("orchestrator")

# Orchestrator decides everything
workflow.add_conditional_edges(
    "orchestrator",
    route_from_orchestrator,
    {
        
        "wait_for_human": "wait_for_human",
        "call_resolve_human_intervention":"call_resolve_human_intervention",
        "cleanup": "cleanup",
        "summarize": "summarize",
        "validate": "validate",
        "notify": "notify",
        "error_handling": "error_handling",
        "end": END
    }
)

# All action nodes go back to orchestrator for next decision
#workflow.add_edge("check_transcript", "orchestrator")
#workflow.add_edge("wait_for_human", "orchestrator")
workflow.add_edge("call_resolve_human_intervention", "orchestrator")
workflow.add_edge("cleanup", "orchestrator")
workflow.add_edge("summarize", "orchestrator")
workflow.add_edge("validate", "orchestrator")
workflow.add_edge("notify", END)
workflow.add_edge("error_handling", "orchestrator")
workflow.add_edge("wait_for_human", END)

# Compile with checkpointing
app_graph = workflow.compile(
    checkpointer=memory
    #interrupt_before=["wait_for_human"]
)

# --- FASTAPI ENDPOINTS ---

app = FastAPI(
    title="Simplified Medical Discharge Summary API",
    description="Clean, LLM-orchestrated discharge summary workflow",
    version="4.0.0"
)

class ConsultationReq(BaseModel):
    consultation_id: str
    patient_id: str
    doctor_id: str
    specialty: str = "General"
    raw_transcript: Optional[str] = None

class TranscriptUpdate(BaseModel):
    raw_transcript: str

@app.post("/consultations", tags=["Consultations"])
def create_consultation(req: ConsultationReq):
    """Create a new consultation"""
    with get_db() as db:
        existing = get_consultation(req.consultation_id, db)
        if existing:
            raise HTTPException(status_code=400, detail="Consultation ID already exists")
        
        consultation = ConsultationDB(
            consultation_id=req.consultation_id,
            patient_id=req.patient_id,
            doctor_id=req.doctor_id,
            specialty=req.specialty,
            raw_transcript=req.raw_transcript
        )
        db.add(consultation)
        
        discharge_summary = DischargeSummaryDB(consultation_id=req.consultation_id)
        db.add(discharge_summary)
        
        db.commit()
        
    update_status(req.consultation_id, "CREATED")
    
    return {
        "message": "Consultation created successfully",
        "consultation_id": req.consultation_id,
        "has_transcript": bool(req.raw_transcript and len(req.raw_transcript.strip()) >= 50),
        "next_step": "Call POST /orchestrate/{consultation_id} to start workflow"
    }

@app.post("/orchestrate/{consultation_id}", tags=["Workflow"])
async def run_orchestration(consultation_id: str):
    """Start or resume the workflow - orchestrator handles everything"""
    with get_db() as db:
        consultation = get_consultation(consultation_id, db)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation ID not found")
    
    config = {
        "configurable": {"thread_id": consultation_id},
        "recursion_limit": 50
    }
    
    try:
        current_state = app_graph.get_state(config)
        
        if current_state and current_state.next:
            # Resume existing workflow
            print(f"\n{'='*80}")
            print(f"[orchestrate] 🔄 RESUMING workflow for {consultation_id}")
            print(f"{'='*80}\n")
            
            final_state = None
            for state in app_graph.stream(None, config, stream_mode="values"):
                final_state = state
        else:
            # Start new workflow
            print(f"\n{'='*80}")
            print(f"[orchestrate] 🚀 STARTING workflow for {consultation_id}")
            print(f"{'='*80}\n")
            
            initial_state = {
                "consultation_id": consultation_id,
                "messages": ["[WORKFLOW] Starting discharge summary workflow"],
                "next_action": None,
                "reasoning": None,
                "completed_actions": []
            }
            
            final_state = None
            for state in app_graph.stream(initial_state, config, stream_mode="values"):
                final_state = state
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Orchestration error: {str(e)}")
    
    # Get current status
    pending_interventions = get_pending_interventions(consultation_id)
    
    with get_db() as db:
        latest_status = db.query(WorkflowStatusDB).filter(
            WorkflowStatusDB.consultation_id == consultation_id
        ).order_by(WorkflowStatusDB.timestamp.desc()).first()
        
        current_status = latest_status.status if latest_status else "UNKNOWN"
    
    response = {
        "status": current_status,
        "workflow_messages": final_state.get("messages", []) if final_state else [],
        "last_action": final_state.get("next_action") if final_state else None,
        "reasoning": final_state.get("reasoning") if final_state else None,
        "completed_actions": final_state.get("completed_actions", []) if final_state else [],
        "waiting_for_human": len(pending_interventions) > 0,
        "polling_active": consultation_id in polling_manager.active_polls
    }
    
    if len(pending_interventions) > 0:
        response["message"] = "⏸️ Workflow paused - waiting for transcript (auto-polling every 30s)"
        response["missing"] = ["raw_transcript"]
    else:
        response["message"] = "✅ Workflow in progress or completed"
    
    return response

@app.post("/consultations/{consultation_id}/provide-transcript", tags=["Data Input"])
def provide_transcript(consultation_id: str, update: TranscriptUpdate):
    """Provide the missing transcript - polling will auto-resume workflow"""
    with get_db() as db:
        consultation = get_consultation(consultation_id, db)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        consultation.raw_transcript = update.raw_transcript
        db.commit()
        
    update_status(consultation_id, "TRANSCRIPT_PROVIDED")
    log_workflow_message(
        consultation_id, 
        f"[HUMAN] Transcript provided ({len(update.raw_transcript)} chars)", 
        "INPUT"
    )
    
    return {
        "message": "✅ Transcript received",
        "consultation_id": consultation_id,
        "transcript_length": len(update.raw_transcript),
        "note": "🤖 Auto-polling will detect and resume within 30 seconds"
    }

@app.get("/consultations/{consultation_id}", tags=["Data Retrieval"])
def get_consultation_data(consultation_id: str):
    """Get complete consultation data"""
    with get_db() as db:
        consultation = get_consultation(consultation_id, db)
        discharge = get_discharge_summary(consultation_id, db)
        medications = get_medications(consultation_id, db)
        
        latest_status = db.query(WorkflowStatusDB).filter(
            WorkflowStatusDB.consultation_id == consultation_id
        ).order_by(WorkflowStatusDB.timestamp.desc()).first()
        
        workflow_logs = db.query(WorkflowLogDB).filter(
            WorkflowLogDB.consultation_id == consultation_id
        ).order_by(WorkflowLogDB.timestamp).all()
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        return {
            "consultation": {
                "id": consultation.consultation_id,
                "patient_id": consultation.patient_id,
                "doctor_id": consultation.doctor_id,
                "specialty": consultation.specialty,
                "has_transcript": bool(consultation.raw_transcript),
                "transcript_length": len(consultation.raw_transcript) if consultation.raw_transcript else 0
            },
            "discharge_summary": {
                "history": discharge.history if discharge else None,
                "diagnosis": discharge.diagnosis if discharge else None,
                "exam_findings": discharge.exam_findings if discharge else None,
                "followup_instructions": discharge.followup_instructions if discharge else None,
                "status": discharge.final_status if discharge else None
            } if discharge else None,
            "medications": [
                {
                    "name": med.name,
                    "dose": med.dose,
                    "frequency": med.frequency
                } for med in medications
            ] if medications else [],
            "workflow_status": latest_status.status if latest_status else None,
            "polling_active": consultation_id in polling_manager.active_polls,
            "logs": [
                {
                    "message": log.message,
                    "type": log.log_type,
                    "timestamp": str(log.timestamp)
                } for log in workflow_logs
            ]
        }

@app.get("/consultations/{consultation_id}/discharge-summary", tags=["Data Retrieval"])
def get_discharge_summary_only(consultation_id: str):
    """Get only the discharge summary"""
    with get_db() as db:
        consultation = get_consultation(consultation_id, db)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        discharge = get_discharge_summary(consultation_id, db)
        if not discharge or not discharge.history:
            raise HTTPException(
                status_code=404, 
                detail="Discharge summary not yet generated"
            )
        
        medications = get_medications(consultation_id, db)
        
        return {
            "consultation_id": consultation_id,
            "patient_id": consultation.patient_id,
            "doctor_id": consultation.doctor_id,
            "discharge_summary": {
                "history": discharge.history,
                "diagnosis": discharge.diagnosis,
                "exam_findings": discharge.exam_findings,
                "medications": [
                    {
                        "name": med.name,
                        "dose": med.dose,
                        "frequency": med.frequency
                    } for med in medications
                ],
                "followup_instructions": discharge.followup_instructions
            },
            "status": discharge.final_status
        }

@app.delete("/consultations/{consultation_id}", tags=["Management"])
def delete_consultation(consultation_id: str):
    """Delete a consultation and stop polling"""
    polling_manager.stop_polling(consultation_id)
    
    with get_db() as db:
        consultation = get_consultation(consultation_id, db)
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        db.delete(consultation)
        db.commit()
    
    return {
        "message": f"Consultation {consultation_id} deleted",
        "polling_stopped": True
    }

@app.get("/stats", tags=["System"])
def get_statistics():
    """Get system statistics"""
    with get_db() as db:
        total = db.query(ConsultationDB).count()
        pending = db.query(HumanInterventionDB).filter(
            HumanInterventionDB.status == "PENDING"
        ).count()
        
        return {
            "total_consultations": total,
            "pending_interventions": pending,
            "active_polling": list(polling_manager.active_polls.keys()),
            "version": "4.0.0 - Simplified"
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
            "version": "4.0.0"
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
        "name": "Simplified Medical Discharge Summary API",
        "version": "4.0.0",
        "description": "Clean workflow with single LLM orchestrator",
        "workflow": [
            "1️⃣ check_transcript - Initial check",
            "2️⃣ orchestrator - LLM decides ALL actions",
            "3️⃣ Actions: cleanup, summarize, validate, notify",
            "4️⃣ Auto-polling if transcript missing"
        ],
        "key_endpoints": {
            "create": "POST /consultations",
            "start_workflow": "POST /orchestrate/{id}",
            "provide_transcript": "POST /consultations/{id}/provide-transcript",
            "get_data": "GET /consultations/{id}",
            "get_summary": "GET /consultations/{id}/discharge-summary"
        },
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("CENLLM:app", host="0.0.0.0", port=8000, reload=True)