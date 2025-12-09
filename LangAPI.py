from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from langgraph.graph import StateGraph, END
from typing import TypedDict

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


# 
# LLM SETUP

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key="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",
)
parser = StrOutputParser()

# ORCHESTRATION STEP FUNCTIONS

def step_speech_to_text(c_id: str):
    
    c = consultations[c_id]
    if not c.raw_transcript:
        #c.raw_transcript = (
         #   "Patient has fever for 3 days and body pain. "
         #   "Examination shows mild dehydration."
        #)
        c.raw_transcript=("Patient is a 32 year old male presenting with fever for the past 3 days, associated with body ache and mild sore throat. "
                          "No cough, no breathlessness. No significant past medical history. "
                          "On examination, temperature is 101°F, pulse 96/min, hydration fair. No rash noted. Throat minimally congested. No organomegaly. Diagnosed likely viral febrile illness. " 
                          "Prescribed paracetamol 500 mg thrice daily and oral hydration. Advised to repeat visit if fever persists beyond 5 days or symptoms worsen.")
    update_status(c_id, "TRANSCRIBED")


def step_cleanup(c_id: str):
    c = consultations[c_id]
    c.cleaned_transcript = (c.raw_transcript or "").strip()
    update_status(c_id, "CLEANED")


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


def step_summarize(c_id: str):
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

    

    # extract only JSON portion
    json_str = re.search(r"\{.*\}", llm_output, re.DOTALL)
    if not json_str:
        raise ValueError("LLM did not return JSON.")

    summary = json.loads(json_str.group())

    d = discharge[c_id]

    # --- history & diagnosis as lists of strings ---
    history = _normalize_str_list(summary.get("history"))
    diagnosis = _normalize_str_list(summary.get("diagnosis"))

    # Backfill if still empty
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

    # --- exam findings ---
    exam_findings = summary.get("exam_findings")
    if not exam_findings or not str(exam_findings).strip():
        exam_findings = "Not clearly documented in the transcript."
    d.exam_findings = str(exam_findings).strip()

    # --- medications ---
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
                meds.append(
                    Medication(
                        name=m.strip(),
                        dose="Not specified",
                        frequency="Not specified",
                    )
                )
    elif isinstance(meds_raw, str) and meds_raw.strip():
        meds.append(
            Medication(
                name=meds_raw.strip(), dose="Not specified", frequency="Not specified"
            )
        )

    d.medications = meds

    # --- follow-up instructions ---
    fup = summary.get("follow_up_instructions") or summary.get("followup_instructions")
    if not fup or not str(fup).strip():
        fup = (
            "No specific follow-up instructions documented; "
            "advise routine follow-up as clinically indicated."
        )
    d.followup_instructions = str(fup).strip()

    # final status
    d.final_status = "SUMMARY_GENERATED"
    update_status(c_id, "SUMMARY_GENERATED")


def step_notify(c_id: str):
    """Notify doctor / mark final status."""
    update_status(c_id, "NOTIFIED_DOCTOR")


# VALIDATION LOGIC

REQUIRED_FIELDS = [
    "history",
    "diagnosis",
    "exam_findings",
    "medications",
    "followup_instructions",
]

def has_required_fields(c_id: str) -> bool:
    """
    Check if required discharge fields are already present.
    If *all* required fields are present and non-empty, return True.
    """
    d = discharge.get(c_id)
    if d is None:
        return False

    if not d.history or len(d.history) == 0:
        return False
    if not d.diagnosis or len(d.diagnosis) == 0:
        return False
    if not d.exam_findings or d.exam_findings.strip() == "":
        return False
    if not d.medications or len(d.medications) == 0:
        return False
    if not d.followup_instructions or d.followup_instructions.strip() == "":
        return False

    return True


# LANGGRAPH STATE + NODES


class OrchestratorState(TypedDict):
    consultation_id: str
    need_summarize: bool


def node_speech_to_text(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    step_speech_to_text(c_id)
    return state


def node_cleanup(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    step_cleanup(c_id)
    return state


def node_validate(state: OrchestratorState) -> OrchestratorState:
    """
    Validation node:
    - If required fields already filled in discharge report:
        -> set need_summarize = False
    - Else:
        -> set need_summarize = True
    """
    c_id = state["consultation_id"]
    if has_required_fields(c_id):
        state["need_summarize"] = False
        update_status(c_id, "VALIDATED_OK")
    else:
        state["need_summarize"] = True
        update_status(c_id, "VALIDATION_MISSING_FIELDS")
    return state


def node_summarize(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    step_summarize(c_id)
    return state


def node_notify(state: OrchestratorState) -> OrchestratorState:
    c_id = state["consultation_id"]
    step_notify(c_id)
    return state


#  Build the LangGraph workflow 

workflow = StateGraph(OrchestratorState)

workflow.add_node("speech_to_text", node_speech_to_text)
workflow.add_node("cleanup", node_cleanup)
workflow.add_node("validate", node_validate)
workflow.add_node("summarize", node_summarize)
workflow.add_node("notify", node_notify)

workflow.set_entry_point("speech_to_text")

# linear edges
workflow.add_edge("speech_to_text", "cleanup")
workflow.add_edge("cleanup", "validate")

# conditional edge from validate:
workflow.add_conditional_edges(
    "validate",
    lambda s: "summarize" if s["need_summarize"] else "notify",
)

# after summarize, always go to notify
workflow.add_edge("summarize", "notify")
workflow.add_edge("notify", END)

app_graph = workflow.compile()


def orchestrate(consultation_id: str):
   
    initial_state: OrchestratorState = {
        "consultation_id": consultation_id,
        "need_summarize": False,
    }
    _ = app_graph.invoke(initial_state)
    return "Workflow Completed"


# FASTAPI


app = FastAPI()


class ConsultationReq(BaseModel):
    consultation_id: str
    patient_id: str
    doctor_id: str
    specialty: str = "General"


@app.post("/consultations")
def create_consultation(req: ConsultationReq):
    consultations[req.consultation_id] = ConsultationData(**req.dict())
    discharge[req.consultation_id] = DischargeData(
        consultation_id=req.consultation_id
    )
    update_status(req.consultation_id, "CREATED")
    return {"message": "Consultation created"}


@app.post("/orchestrate")
def run_orch(consultation_id: str):
    if consultation_id not in consultations:
        raise HTTPException(status_code=404, detail="ID not found")
    orchestrate(consultation_id)
    return {"status": status[consultation_id]}


@app.get("/consultations/{consultation_id}")
def get_data(consultation_id: str):
    return {
        "consultation": consultations.get(consultation_id),
        "discharge_summary": discharge.get(consultation_id),
        "status": status.get(consultation_id),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("LangAPI:app", host="0.0.0.0", port=8000, reload=True)
