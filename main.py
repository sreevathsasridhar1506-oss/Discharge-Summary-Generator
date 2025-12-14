from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Dict, List, Optional
from datetime import datetime
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
#from langchain_openai import ChatOpenAI

#load_dotenv()
#GROQ_API_KEY = os.getenv("GROQ_API_KEY")


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
    raw_transcript: Optional[str] = None
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


# GROQ LLM
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key="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")
print(llm.invoke("test").content)

parser = StrOutputParser()


# ORCHESTRATOR FUNCTIONS
def step_speech_to_text(c_id: str):
    c = consultations[c_id]
    c.raw_transcript = "Patient has fever for 3 days and body pain. Examination shows mild dehydration."
    update_status(c_id, "TRANSCRIBED")


def step_cleanup(c_id: str):
    c = consultations[c_id]
    c.cleaned_transcript = c.raw_transcript.strip()
    update_status(c_id, "CLEANED")

'''
def step_summarize(c_id: str):
    c = consultations[c_id]
    prompt = ChatPromptTemplate.from_template("""
    Convert transcript to structured discharge JSON only.

    Transcript: {text}
    """)
    chain = prompt | llm | parser
    output = chain.invoke({"text": c.cleaned_transcript})
    summary = eval(output)

    d = discharge[c_id]
    d.history = summary.get("history")
    d.diagnosis = summary.get("diagnosis")
    d.exam_findings = summary.get("exam_findings")
    d.medications = [Medication(**m) for m in summary.get("medications", [])]
    d.followup_instructions = summary.get("followup_instructions")
    d.final_status = "SUMMARY_GENERATED"
    update_status(c_id, "SUMMARY_GENERATED")
'''
import json
import re

def step_summarize(c_id: str):
    c = consultations[c_id]

    prompt = ChatPromptTemplate.from_template("""
    You are a medical discharge summary assistant.
    Summarize the following cleaned transcript into JSON with the fields:
    chief_complaint, history, exam_findings, diagnosis, investigations, medications, follow_up_instructions.Put follow_up_instructions as a string.

    Return STRICT VALID JSON ONLY. No markdown. No explanation. 

    Transcript:
    {transcript}
    """)


    chain = prompt | llm | parser
    llm_output = chain.invoke({"transcript": c.cleaned_transcript})

    # extract only JSON portion
    json_str = re.search(r"\{.*\}", llm_output, re.DOTALL)
    if not json_str:
        raise ValueError("LLM did not return JSON.")

    summary = json.loads(json_str.group())

    d = discharge[c_id]
    d.history = summary.get("history")
    d.diagnosis = summary.get("diagnosis")
    d.exam_findings = summary.get("exam_findings")
    d.medications = [Medication(**m) for m in summary.get("medications", [])]
    d.followup_instructions = summary.get("followup_instructions")
    d.final_status = "SUMMARY_GENERATED"

    update_status(c_id, "SUMMARY_GENERATED")

def step_notify(c_id: str):
    update_status(c_id, "NOTIFIED_DOCTOR")


def orchestrate(c_id: str):
    step_speech_to_text(c_id)
    step_cleanup(c_id)
    step_summarize(c_id)
    step_notify(c_id)
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
    discharge[req.consultation_id] = DischargeData(consultation_id=req.consultation_id)
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
        "status": status.get(consultation_id)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
