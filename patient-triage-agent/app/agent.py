# ruff: noqa
# Copyright 2026 Google LLC
"""Healthcare & Patient Triage Agent built with Google ADK Workflow."""

import datetime
import json
import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.workflow import START, Workflow
from google.genai import types

MODEL = "gemini-2.5-flash"


class VitalSigns(BaseModel):
    heart_rate_bpm: int = Field(default=72, description="Heart rate in beats per minute")
    blood_pressure_sys: int = Field(default=120, description="Systolic blood pressure (mmHg)")
    blood_pressure_dia: int = Field(default=80, description="Diastolic blood pressure (mmHg)")
    temperature_f: float = Field(default=98.6, description="Body temperature in Fahrenheit")
    oxygen_sat_pct: int = Field(default=98, description="Oxygen saturation percentage (SpO2)")


class PatientSymptomReport(BaseModel):
    patient_id: str = Field(default="PAT-1001", description="Patient unique identifier")
    patient_name: str = Field(default="Jane Doe", description="Patient full name")
    age: int = Field(default=35, description="Patient age")
    primary_symptom: str = Field(description="Primary reported medical symptom")
    symptom_duration: str = Field(default="24 hours", description="Duration of symptoms")
    vitals: VitalSigns = Field(default_factory=VitalSigns, description="Patient vital signs")
    medical_history: List[str] = Field(default_factory=list, description="Relevant medical history")


class TriageDecision(BaseModel):
    case_id: str
    triage_level: str  # "ROUTINE_CARE", "PHYSICIAN_REVIEWED_URGENT", "EMERGENCY_ER", "REJECTED"
    triaged_by: str  # "AUTOMATED_TRIAGE" or "ATTENDING_PHYSICIAN"
    notes: str
    care_instructions: str


def parse_and_triage_symptoms(ctx: Context, node_input: Any) -> Event:
    """Parses incoming symptom reports and determines clinical routing."""
    raw_text = ""
    if isinstance(node_input, types.Content):
        for part in node_input.parts:
            if hasattr(part, "text") and part.text:
                raw_text += part.text + " "
            elif hasattr(part, "function_response") and part.function_response:
                resp = part.function_response.response
                if isinstance(resp, dict) and "response" in resp:
                    raw_text += resp["response"] + " "
    elif isinstance(node_input, str):
        raw_text = node_input
    elif isinstance(node_input, dict):
        raw_text = json.dumps(node_input)
    else:
        raw_text = str(node_input)

    # Check if returning from physician review interrupt
    if ctx.state and "patient_report" in ctx.state and ctx.state.get("has_red_flags"):
        if any(keyword in raw_text.upper() for keyword in ["APPROVE", "REJECT", "ER", "CLINIC", "URGENT"]):
            ctx.state["physician_response"] = raw_text.strip()
        return Event(
            output=ctx.state["patient_report"],
            route="physician_review_node",
        )

    temp_f = 98.6
    temp_match = re.search(r"(?:fever|temp|temperature)\s*(?:of|=|:)?\s*([0-9]{2,3}(?:\.[0-9])?)", raw_text, re.IGNORECASE)
    if temp_match:
        try:
            temp_f = float(temp_match.group(1))
        except ValueError:
            temp_f = 98.6

    o2_pct = 98
    o2_match = re.search(r"(?:o2|spo2|oxygen)\s*(?:of|=|:)?\s*([0-9]{2,3})%?", raw_text, re.IGNORECASE)
    if o2_match:
        try:
            o2_pct = int(o2_match.group(1))
        except ValueError:
            o2_pct = 98

    hr_bpm = 72
    hr_match = re.search(r"(?:hr|pulse|heart rate)\s*(?:of|=|:)?\s*([0-9]{2,3})", raw_text, re.IGNORECASE)
    if hr_match:
        try:
            hr_bpm = int(hr_match.group(1))
        except ValueError:
            hr_bpm = 72

    bp_sys = 120
    bp_match = re.search(r"(?:bp|blood pressure)\s*(?:of|=|:)?\s*([0-9]{2,3})/([0-9]{2,3})", raw_text, re.IGNORECASE)
    if bp_match:
        try:
            bp_sys = int(bp_match.group(1))
        except ValueError:
            bp_sys = 120

    vitals = VitalSigns(
        heart_rate_bpm=hr_bpm,
        blood_pressure_sys=bp_sys,
        temperature_f=temp_f,
        oxygen_sat_pct=o2_pct,
    )

    red_flag_keywords = [
        "chest pain", "shortness of breath", "severe dizziness", "fainting",
        "numbness", "seizure", "unconscious", "stroke", "severe fever", "bleeding"
    ]
    has_red_flags = (
        temp_f >= 102.5 or
        o2_pct < 93 or
        bp_sys >= 160 or bp_sys <= 90 or
        hr_bpm >= 120 or hr_bpm <= 50 or
        any(kw in raw_text.lower() for kw in red_flag_keywords)
    )

    patient_report = PatientSymptomReport(
        patient_id="PAT-1001",
        patient_name="Jane Doe",
        age=35,
        primary_symptom=raw_text.strip() or "General health inquiry and symptom report",
        symptom_duration="12-24 hours",
        vitals=vitals,
        medical_history=["Hypertension", "Asthma"] if has_red_flags else ["None"],
    )

    route = "physician_review_node" if has_red_flags else "routine_care_node"

    return Event(
        output=patient_report.model_dump(),
        route=route,
        state={
            "patient_report": patient_report.model_dump(),
            "has_red_flags": has_red_flags,
        },
    )


def routine_care_node(node_input: Dict[str, Any]) -> TriageDecision:
    """Auto-triage node for stable, low-risk patient reports."""
    report = PatientSymptomReport(**node_input) if isinstance(node_input, dict) else node_input
    case_id = f"TRIAGE-{int(datetime.datetime.now().timestamp())}"
    return TriageDecision(
        case_id=case_id,
        triage_level="ROUTINE_CARE",
        triaged_by="AUTOMATED_TRIAGE",
        notes=f"🟢 [ROUTINE CARE APPROVED] Vitals are stable (Temp: {report.vitals.temperature_f}°F, SpO2: {report.vitals.oxygen_sat_pct}%). No clinical red flags detected.",
        care_instructions="Prescribed rest, hydration, and routine Telehealth nurse check-in within 48 hours.",
    )


async def physician_review_node(ctx: Context, node_input: Dict[str, Any]):
    """Human-in-the-loop review node for urgent or high-risk patient reports."""
    report_data = ctx.state.get("patient_report") or node_input
    report = PatientSymptomReport(**report_data) if isinstance(report_data, dict) else report_data
    interrupt_id = "doctor_review"

    physician_input = None
    if ctx.resume_inputs and interrupt_id in ctx.resume_inputs:
        physician_input = str(ctx.resume_inputs[interrupt_id])
    elif "physician_response" in ctx.state:
        physician_input = str(ctx.state["physician_response"])

    if not physician_input:
        yield RequestInput(
            interrupt_id=interrupt_id,
            message=(
                f"🚨 [PHYSICIAN REVIEW REQUIRED] Patient '{report.patient_name}' (ID: {report.patient_id}, Age: {report.age}) "
                f"reported '{report.primary_symptom}'. Vitals: Temp {report.vitals.temperature_f}°F, HR {report.vitals.heart_rate_bpm} bpm, "
                f"BP {report.vitals.blood_pressure_sys}/{report.vitals.blood_pressure_dia}, SpO2 {report.vitals.oxygen_sat_pct}%.\n"
                f"Clinical Red Flags Detected. Please reply with 'APPROVE_ER' or 'ROUTINE_CLINIC' (e.g. 'APPROVE_ER - Direct patient to Emergency Room immediately')."
            ),
        )
        return

    triage_level = "EMERGENCY_ER" if "ER" in physician_input.upper() or "APPROVE" in physician_input.upper() else "PHYSICIAN_REVIEWED_URGENT"
    case_id = f"TRIAGE-{int(datetime.datetime.now().timestamp())}"

    decision = TriageDecision(
        case_id=case_id,
        triage_level=triage_level,
        triaged_by="ATTENDING_PHYSICIAN",
        notes=f"👨‍⚕️ [PHYSICIAN DECISION: {triage_level}] Attending physician review completed for {report.patient_name}. Doctor Notes: '{physician_input}'",
        care_instructions="Patient directed per physician clinical order." if triage_level == "EMERGENCY_ER" else "Urgent outpatient clinic appointment scheduled.",
    )
    yield Event(output=decision.model_dump())


def format_triage_summary(node_input: Any):
    """Formats triage decision for display in CLI/UI."""
    if isinstance(node_input, TriageDecision):
        res = node_input
    elif isinstance(node_input, dict):
        res = TriageDecision(**node_input)
    else:
        res = TriageDecision(
            case_id="TRIAGE-UNKNOWN",
            triage_level="PROCESSED",
            triaged_by="SYSTEM",
            notes=str(node_input),
            care_instructions="Follow up with primary care physician.",
        )

    summary_text = (
        f"\n==================================================\n"
        f"🏥 PATIENT TRIAGE & CLINICAL SUMMARY\n"
        f"==================================================\n"
        f"• Case ID:      {res.case_id}\n"
        f"• Triage Level: {res.triage_level}\n"
        f"• Triaged By:   {res.triaged_by}\n"
        f"• Notes:        {res.notes}\n"
        f"• Instructions: {res.care_instructions}\n"
        f"==================================================\n"
    )

    yield Event(content=types.Content(role="model", parts=[types.Part.from_text(text=summary_text)]))
    yield Event(output=res.model_dump())


edges = [
    (START, parse_and_triage_symptoms),
    (
        parse_and_triage_symptoms,
        {
            "routine_care_node": routine_care_node,
            "physician_review_node": physician_review_node,
        },
    ),
    (routine_care_node, format_triage_summary),
    (physician_review_node, format_triage_summary),
]

root_agent = Workflow(
    name="patient_triage_agent",
    description="Healthcare & Patient Triage workflow that auto-triages routine symptoms and pauses for attending physician review on clinical red flags.",
    edges=edges,
)

app = App(
    root_agent=root_agent,
    name="app",
)


class PatientTriageReasoningEngine:
    """Vertex AI ReasoningEngine wrapper for ADK Patient Triage App."""

    def __init__(self, app_instance=None):
        self.app = app_instance or app

    def set_up(self):
        """Called upon deployment initialization on Vertex AI Agent Runtime."""
        if not hasattr(self, "app") or self.app is None:
            self.app = app
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app=self.app,
            session_service=self.session_service,
        )

    def query(self, user_id: str = "default-user", session_id: str = "default-session", message: Any = "Hello", **kwargs) -> str:
        """Synchronous query method."""
        import asyncio
        return asyncio.run(self.async_stream_query(user_id=user_id, session_id=session_id, message=message, **kwargs))

    async def async_stream_query(self, user_id: str = "default-user", session_id: str = "default-session", message: Any = "Hello", **kwargs) -> str:
        """Asynchronous streaming query method."""
        if not session_id:
            session_id = str(uuid.uuid4())

        try:
            await self.session_service.get_session(user_id=user_id, session_id=session_id)
        except Exception:
            await self.session_service.create_session(user_id=user_id, session_id=session_id)

        responses = []
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            input=message,
        ):
            if hasattr(event, "content") and event.content:
                for part in getattr(event.content, "parts", []):
                    if hasattr(part, "text") and part.text:
                        responses.append(part.text)

        return "\n".join(responses) if responses else "Patient triage session processed."

