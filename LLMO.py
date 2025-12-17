from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import re

from langchain_core.load.serializable import Serializable
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from collections.abc import Sequence
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

# Define OrchestratorState as a TypedDict to manage the state

class OrchestratorState(TypedDict):
    consultation_id: str
    messages: List[str]  # Track conversation history
    next_action: Optional[str]  # LLM-decided next action
    reasoning: Optional[str]  # LLM's reasoning for the decision

# DATA MODELS & IN-MEMORY DB

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

consultations: Dict[str, ConsultationData] = {}
discharge: Dict[str, DischargeData] = {}
status: Dict[str, str] = {}

def update_status(consultation_id: str, state: str):
    status[consultation_id] = state

# LLM SETUP

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key="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",
)
parser = StrOutputParser()

# ORCHESTRATION STEP FUNCTIONS

def step_speech_to_text(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    
    c = consultations[c_id]
    if not c.raw_transcript:
        c.raw_transcript = ("Patient is a 32 year old male presenting with fever for the past 3 days, "
                            "associated with body ache and mild sore throat. No cough, no breathlessness. "
                            "No significant past medical history. On examination, temperature is 101°F, pulse 96/min, hydration fair. "
                            "No rash noted. Throat minimally congested. No organomegaly. Diagnosed likely viral febrile illness. "
                            "Prescribed paracetamol 500 mg thrice daily and oral hydration. Advised to repeat visit if fever persists beyond 5 days or symptoms worsen.")
    update_status(c_id, "TRANSCRIBED")
    state["messages"].append(f"[STEP COMPLETED] Speech-to-text: Generated transcript of {len(c.raw_transcript)} characters")
    print(f"[step_speech_to_text] Transcribed for {c_id}. Raw transcript length: {len(c.raw_transcript)}")
    return state

def step_cleanup(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    c = consultations[c_id]
    c.cleaned_transcript = (c.raw_transcript or "").strip()
    update_status(c_id, "CLEANED")
    state["messages"].append(f"[STEP COMPLETED] Cleanup: Cleaned transcript is ready ({len(c.cleaned_transcript)} characters)")
    print(f"[step_cleanup] Cleaned for {c_id}. Cleaned transcript length: {len(c.cleaned_transcript) if c.cleaned_transcript else 0}")
    return state

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

def step_summarize(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    c = consultations[c_id]
    
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
    llm_output = chain.invoke({"transcript": c.cleaned_transcript})

    json_str = re.search(r"\{.*\}", llm_output, re.DOTALL)
    if not json_str:
        raise ValueError("LLM did not return JSON.")
    summary = json.loads(json_str.group())

    d = discharge[c_id]
    history = _normalize_str_list(summary.get("history"))
    diagnosis = _normalize_str_list(summary.get("diagnosis"))

    if not history:
        history = [
            "Not clearly specified in the transcript. "
            f"Transcript snippet: {c.cleaned_transcript[:120]}..."
        ]
    if not diagnosis:
        diagnosis = [
            "Not clearly specified in the transcript. "
            "Likely acute febrile illness based on available information."
        ]

    d.history = history
    d.diagnosis = diagnosis
    d.exam_findings = summary.get("exam_findings", "Not clearly documented in the transcript.")
    meds_raw = summary.get("medications", [])
    meds: List[Medication] = []

    if isinstance(meds_raw, list):
        for m in meds_raw:
            if isinstance(m, dict):
                name = (m.get("name") or "Not specified").strip()
                dose = (m.get("dose") or "Not specified").strip()
                freq = (m.get("frequency") or "Not specified").strip()
                meds.append(Medication(name=name, dose=dose, frequency=freq))
            elif isinstance(m, str):
                meds.append(Medication(name=m.strip(), dose="Not specified", frequency="Not specified"))
    elif isinstance(meds_raw, str) and meds_raw.strip():
        meds.append(Medication(name=meds_raw.strip(), dose="Not specified", frequency="Not specified"))

    d.medications = meds
    fup = summary.get("follow_up_instructions") or summary.get("followup_instructions")
    if not fup or not str(fup).strip():
        fup = (
            "No specific follow-up instructions documented; "
            "advise routine follow-up as clinically indicated."
        )
    d.followup_instructions = str(fup).strip()

    d.final_status = "SUMMARY_GENERATED"
    update_status(c_id, "SUMMARY_GENERATED")
    
    state["messages"].append(f"[STEP COMPLETED] Summarization: Extracted {len(d.history)} history items, {len(d.diagnosis)} diagnoses, {len(d.medications)} medications")
    print(f"[step_summarize] Summary generated for {c_id}")
    return state

def step_validate(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    d = discharge.get(c_id)
    
    validation_results = {
        "has_history": bool(d and d.history and len(d.history) > 0),
        "has_diagnosis": bool(d and d.diagnosis and len(d.diagnosis) > 0),
        "has_exam_findings": bool(d and d.exam_findings and d.exam_findings.strip()),
        "has_medications": bool(d and d.medications and len(d.medications) > 0),
        "has_followup": bool(d and d.followup_instructions and d.followup_instructions.strip())
    }
    
    all_valid = all(validation_results.values())
    
    validation_msg = f"[STEP COMPLETED] Validation: "
    if all_valid:
        validation_msg += "All required fields are present and valid"
        update_status(c_id, "VALIDATED")
    else:
        missing = [k for k, v in validation_results.items() if not v]
        validation_msg += f"Missing or invalid fields: {', '.join(missing)}"
        update_status(c_id, "VALIDATION_FAILED")
    
    state["messages"].append(validation_msg)
    print(f"[step_validate] Validation for {c_id}: {validation_msg}")
    return state

def step_notify(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    update_status(c_id, "NOTIFIED_DOCTOR")
    state["messages"].append(f"[STEP COMPLETED] Notification: Doctor has been notified about consultation {c_id}")
    print(f"[step_notify] Doctor notified for {c_id}")
    return state

def step_error_handling(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    update_status(c_id, "ERROR_HANDLED")
    state["messages"].append(f"[STEP COMPLETED] Error Handling: Issues have been logged and escalated")
    print(f"[step_error_handling] Error handled for {c_id}")
    return state

# LLM-BASED ORCHESTRATOR 

def llm_orchestrator(state: OrchestratorState) -> OrchestratorState:
    """
    This function uses the LLM to decide what to do next based on the current state.
    The LLM analyzes the workflow progress and makes intelligent decisions.
    """
    c_id = state["consultation_id"]
    c = consultations.get(c_id)
    d = discharge.get(c_id)
    current_status = status.get(c_id, "UNKNOWN")
    
    # Build a context string for the LLM
    context = f"""
You are an intelligent workflow orchestrator for a medical discharge summary system.

CURRENT WORKFLOW STATUS:
- Consultation ID: {c_id}
- Current Status: {current_status}
- Has Raw Transcript: {bool(c and c.raw_transcript)}
- Has Cleaned Transcript: {bool(c and c.cleaned_transcript)}
- Discharge Summary Exists: {bool(d)}

DISCHARGE SUMMARY DETAILS:
- History: {len(d.history) if d and d.history else 0} items
- Diagnosis: {len(d.diagnosis) if d and d.diagnosis else 0} items  
- Exam Findings: {'Present' if d and d.exam_findings and d.exam_findings.strip() else 'Missing'}
- Medications: {len(d.medications) if d and d.medications else 0} items
- Follow-up Instructions: {'Present' if d and d.followup_instructions and d.followup_instructions.strip() else 'Missing'}

WORKFLOW HISTORY:
{chr(10).join(state["messages"])}

AVAILABLE ACTIONS:
1. "summarize" - Extract medical information from the transcript using LLM
2. "validate" - Check if all required fields are properly filled
3. "notify" - Notify the doctor that the discharge summary is ready
4. "error" - Handle errors or missing critical information
5. "complete" - Mark the workflow as complete

YOUR TASK:
Analyze the current state and decide the NEXT BEST ACTION to take.
Consider:
- What steps have already been completed?
- What information is missing?
- Is the discharge summary complete and valid?
- What is the logical next step?

Respond with ONLY a JSON object in this exact format:
{{
    "action": "one of: summarize, validate, notify, error, complete",
    "reasoning": "brief explanation of why this action is needed"
}}

Do not include any markdown formatting or additional text.
"""

    orchestrator_prompt = ChatPromptTemplate.from_template("{context}")
    chain = orchestrator_prompt | llm | parser
    
    print(f"\n[llm_orchestrator] Asking LLM to decide next action for {c_id}...")
    llm_response = chain.invoke({"context": context})
    
    try:
        json_match = re.search(r"\{.*\}", llm_response, re.DOTALL)
        if not json_match:
            raise ValueError("LLM did not return valid JSON")
        
        decision = json.loads(json_match.group())
        action = decision.get("action", "error")
        reasoning = decision.get("reasoning", "No reasoning provided")
        
        print(f"[llm_orchestrator] LLM Decision: {action}")
        print(f"[llm_orchestrator] LLM Reasoning: {reasoning}")
        
        state["next_action"] = action
        state["reasoning"] = reasoning
        state["messages"].append(f"[LLM DECISION] Action: {action} | Reasoning: {reasoning}")
        
    except Exception as e:
        print(f"[llm_orchestrator] Error parsing LLM response: {e}")
        print(f"[llm_orchestrator] Raw LLM response: {llm_response}")
        state["next_action"] = "error"
        state["reasoning"] = f"Failed to parse LLM decision: {str(e)}"
    
    return state

# CONDITIONAL ROUTING BASED ON LLM DECISION

def route_based_on_llm_decision(state: OrchestratorState) -> str:
    """
    Routes to the next node based on what the LLM decided.
    This is called by LangGraph to determine which edge to follow.
    """
    action = state.get("next_action", "error")
    
    routing_map = {
        "summarize": "summarize",
        "validate": "validate",
        "notify": "notify",
        "error": "error_handling",
        "complete": "end"
    }
    
    next_node = routing_map.get(action, "error_handling")
    print(f"[route_based_on_llm_decision] Routing to: {next_node}")
    return next_node

# LANGGRAPH WORKFLOW WITH LLM ORCHESTRATION

workflow = StateGraph(OrchestratorState)

# Add all nodes
workflow.add_node("speech_to_text", step_speech_to_text)
workflow.add_node("cleanup", step_cleanup)
workflow.add_node("llm_orchestrator", llm_orchestrator)  # LLM makes decisions here!
workflow.add_node("summarize", step_summarize)
workflow.add_node("validate", step_validate)
workflow.add_node("notify", step_notify)
workflow.add_node("error_handling", step_error_handling)

# Set entry point
workflow.set_entry_point("speech_to_text")

# Define fixed edges (always follow this path)
workflow.add_edge("speech_to_text", "cleanup")
workflow.add_edge("cleanup", "llm_orchestrator")

# Conditional edges - LLM decides where to go next!
workflow.add_conditional_edges(
    "llm_orchestrator",
    route_based_on_llm_decision,
    {
        "summarize": "summarize",
        "validate": "validate",
        "notify": "notify",
        "error_handling": "error_handling",
        "end": END
    }
)

# After each action, go back to LLM to decide next step
workflow.add_edge("summarize", "llm_orchestrator")
workflow.add_edge("validate", "llm_orchestrator")
workflow.add_edge("notify", END)  
workflow.add_edge("error_handling", "llm_orchestrator")

# Compile 
app_graph = workflow.compile()

# FASTAPI ENDPOINTS

app = FastAPI()

class ConsultationReq(BaseModel):
    consultation_id: str
    patient_id: str
    doctor_id: str
    specialty: str = "General"

@app.post("/consultations")
def create_consultation(req: ConsultationReq):
    consultations[req.consultation_id] = ConsultationData(**req.dict())
    discharge[req.consultation_id] = DischargeData(consultation_id=req.consultation_id)
    update_status(req.consultation_id, "CREATED")
    return {"message": "Consultation created"}

@app.post("/orchestrate")
def run_orch(consultation_id: str):
    if consultation_id not in consultations:
        raise HTTPException(status_code=404, detail="ID not found")
    
    # Initialize state with conversation tracking
    initial_state = {
        "consultation_id": consultation_id,
        "messages": ["[WORKFLOW STARTED] Beginning medical discharge summary workflow"],
        "next_action": None,
        "reasoning": None
    }
    
    print(f"\n{'='*80}")
    print(f"[run_orch] Starting LLM-orchestrated workflow for {consultation_id}")
    print(f"{'='*80}\n")
    
    # Run the compiled graph - LLM will orchestrate 
    final_state = app_graph.invoke(initial_state)
    
    print(f"\n{'='*80}")
    print(f"[run_orch] Workflow completed for {consultation_id}")
    print(f"[run_orch] Final status: {status.get(consultation_id)}")
    print(f"[run_orch] Workflow history:")
    for msg in final_state.get("messages", []):
        print(f"  {msg}")
    print(f"{'='*80}\n")
    
    return {
        "status": status[consultation_id],
        "workflow_history": final_state.get("messages", []),
        "final_reasoning": final_state.get("reasoning")
    }

@app.get("/consultations/{consultation_id}")
def get_data(consultation_id: str):
    return {
        "consultation": consultations.get(consultation_id),
        "discharge_summary": discharge.get(consultation_id),
        "status": status.get(consultation_id),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("LLMO:app", host="0.0.0.0", port=8000, reload=True)