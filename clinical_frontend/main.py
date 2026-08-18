import json
import os
import re
import requests
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
import google.auth
import google.auth.transport.requests

app = FastAPI(title="Doctor Triage Portal & Clinical Dashboard", version="1.0.0")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
AGENT_RUNTIME_ID = os.environ.get("AGENT_RUNTIME_ID", "")


def get_numeric_engine_id(resource_path: str) -> str:
    """Extracts numeric ID from Reasoning Engine resource path."""
    if "/" in resource_path:
        return resource_path.split("/")[-1]
    return resource_path


class TriageActionRequest(BaseModel):
    action: str  # "APPROVE_ER" or "ROUTINE_CLINIC" or "REJECT"
    notes: Optional[str] = ""
    user_id: Optional[str] = "default-user"


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the Doctor Triage Portal UI."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Doctor Triage Portal | Ambient Healthcare AI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #070b12;
            --bg-card: rgba(255, 255, 255, 0.03);
            --bg-card-hover: rgba(255, 255, 255, 0.06);
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-red: rgba(239, 68, 68, 0.3);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --red-glow: rgba(239, 68, 68, 0.15);
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-deep);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(239, 68, 68, 0.08) 0%, transparent 40%);
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-glass);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .brand-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #ef4444, #b91c1c);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 0 20px var(--red-glow);
        }

        .brand h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff, #9ca3af);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .status-badge {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 1.5rem;
        }

        .patient-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-red);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .patient-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #ef4444, #f59e0b);
        }

        .patient-card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.5), 0 0 20px var(--red-glow);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .patient-name {
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 600;
        }

        .patient-meta {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.2rem;
        }

        .urgent-badge {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: var(--accent-red);
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.05em;
        }

        .vitals-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            margin: 1rem 0;
            background: rgba(0,0,0,0.2);
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .vital-item {
            display: flex;
            flex-direction: column;
        }

        .vital-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .vital-value {
            font-size: 1rem;
            font-weight: 600;
            margin-top: 0.2rem;
        }

        .symptom-box {
            font-size: 0.9rem;
            color: var(--text-primary);
            line-height: 1.4;
            margin-bottom: 1.25rem;
            padding: 0.75rem;
            background: rgba(255,255,255,0.02);
            border-left: 3px solid var(--accent-red);
            border-radius: 4px;
        }

        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
        }

        .btn {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        .btn-er {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }

        .btn-er:hover {
            background: linear-gradient(135deg, #dc2626, #b91c1c);
            box-shadow: 0 6px 16px rgba(239, 68, 68, 0.5);
        }

        .btn-clinic {
            background: rgba(255,255,255,0.08);
            color: var(--text-primary);
            border: 1px solid var(--border-glass);
        }

        .btn-clinic:hover {
            background: rgba(255,255,255,0.15);
        }

        .empty-state {
            grid-column: 1 / -1;
            text-align: center;
            padding: 4rem 2rem;
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border-glass);
        }

        .empty-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }

        .loading-spinner {
            border: 3px solid rgba(255,255,255,0.1);
            border-top: 3px solid var(--accent-red);
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
            margin: 2rem auto;
        }

        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">
            <div class="brand-icon">🏥</div>
            <div>
                <h1>Doctor Triage Portal</h1>
                <p style="color: var(--text-secondary); font-size: 0.85rem;">Ambient Healthcare AI System</p>
            </div>
        </div>
        <div class="status-badge">
            <div class="pulse-dot"></div>
            Clinical Engine Connected
        </div>
    </div>

    <h2 style="font-family: 'Outfit'; font-size: 1.3rem; margin-bottom: 1rem; color: var(--text-secondary);">
        Urgent Patient Reviews Required
    </h2>

    <div id="loading" class="loading-spinner"></div>
    <div id="cards-container" class="dashboard-grid" style="display: none;"></div>

    <script>
        async function fetchPendingTriage() {
            try {
                const res = await fetch('/api/pending');
                const data = await res.json();
                const container = document.getElementById('cards-container');
                const loading = document.getElementById('loading');
                
                loading.style.display = 'none';
                container.style.display = 'grid';
                container.innerHTML = '';

                if (!data.pending || data.pending.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">✅</div>
                            <h3 style="font-family: 'Outfit'; margin-bottom: 0.5rem;">All Patient Triage Cases Resolved</h3>
                            <p style="color: var(--text-secondary);">No pending urgent doctor reviews in the queue.</p>
                        </div>
                    `;
                    return;
                }

                data.pending.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'patient-card';
                    card.innerHTML = `
                        <div class="card-header">
                            <div>
                                <div class="patient-name">${item.report.patient_name || 'Jane Doe'}</div>
                                <div class="patient-meta">ID: ${item.report.patient_id || 'PAT-1001'} • Age: ${item.report.age || 35}</div>
                            </div>
                            <span class="urgent-badge">🚨 RED FLAG</span>
                        </div>
                        
                        <div class="symptom-box">
                            <strong>Primary Symptom:</strong> ${item.report.primary_symptom || 'Reported medical symptoms requiring physician attention.'}
                        </div>

                        <div class="vitals-grid">
                            <div class="vital-item">
                                <span class="vital-label">Temperature</span>
                                <span class="vital-value" style="color: #ef4444;">${item.report.vitals?.temperature_f || 102.5}°F</span>
                            </div>
                            <div class="vital-item">
                                <span class="vital-label">SpO2 Oxygen</span>
                                <span class="vital-value" style="color: #f59e0b;">${item.report.vitals?.oxygen_sat_pct || 91}%</span>
                            </div>
                            <div class="vital-item">
                                <span class="vital-label">Heart Rate</span>
                                <span class="vital-value">${item.report.vitals?.heart_rate_bpm || 105} bpm</span>
                            </div>
                            <div class="vital-item">
                                <span class="vital-label">Blood Pressure</span>
                                <span class="vital-value">${item.report.vitals?.blood_pressure_sys || 145}/${item.report.vitals?.blood_pressure_dia || 90}</span>
                            </div>
                        </div>

                        <div class="btn-group">
                            <button class="btn btn-er" onclick="submitDecision('${item.session_id}', 'APPROVE_ER')">
                                🚨 Approve ER
                            </button>
                            <button class="btn btn-clinic" onclick="submitDecision('${item.session_id}', 'ROUTINE_CLINIC')">
                                🩺 Routine Clinic
                            </button>
                        </div>
                    `;
                    container.appendChild(card);
                });
            } catch (err) {
                console.error("Failed to fetch pending triage cases:", err);
            }
        }

        async function submitDecision(sessionId, action) {
            try {
                const res = await fetch(`/api/action/${sessionId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: action, notes: `${action} decision submitted by attending physician.` })
                });
                const result = await res.json();
                alert(`Triage decision submitted: ${action}`);
                fetchPendingTriage();
            } catch (err) {
                alert("Error submitting physician decision: " + err);
            }
        }

        fetchPendingTriage();
        setInterval(fetchPendingTriage, 10000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/api/pending")
async def get_pending_reviews():
    """Queries ADK VertexAiSessionService for active patient sessions with pending doctor reviews."""
    try:
        credentials, project = google.auth.default()
        numeric_engine_id = get_numeric_engine_id(AGENT_RUNTIME_ID)
        session_service = VertexAiSessionService(
            project=PROJECT_ID,
            location=LOCATION,
            agent_engine_id=numeric_engine_id
        )

        all_sessions = []
        for user_id in ["default-user", "cli-user", "triage-user"]:
            try:
                sessions = await session_service.list_sessions(user_id=user_id)
                for s in sessions:
                    s["user_id"] = user_id
                all_sessions.extend(sessions)
            except Exception:
                pass

        pending_items = []
        for session in all_sessions:
            sess_id = session.get("id") or session.get("name")
            if "/" in sess_id:
                sess_id = sess_id.split("/")[-1]
            user_id = session.get("user_id", "default-user")

            try:
                sess_obj = await session_service.get_session(user_id=user_id, session_id=sess_id)
                events = getattr(sess_obj, "events", []) or []

                unresolved_interrupts = {}
                for ev in events:
                    if hasattr(ev, "content") and ev.content and hasattr(ev.content, "parts"):
                        for part in ev.content.parts:
                            if hasattr(part, "function_call") and part.function_call:
                                fn_call = part.function_call
                                if getattr(fn_call, "name", "") == "adk_request_input":
                                    call_id = getattr(fn_call, "id", "doctor_review")
                                    unresolved_interrupts[call_id] = fn_call
                            elif hasattr(part, "function_response") and part.function_response:
                                fn_resp = part.function_response
                                if getattr(fn_resp, "name", "") == "adk_request_input":
                                    resp_id = getattr(fn_resp, "id", "doctor_review")
                                    unresolved_interrupts.pop(resp_id, None)

                if unresolved_interrupts:
                    for interrupt_id, fn_call in unresolved_interrupts.items():
                        args = getattr(fn_call, "args", {}) or {}
                        msg = args.get("message", "Physician review required.")

                        pending_items.append({
                            "session_id": sess_id,
                            "user_id": user_id,
                            "interrupt_id": interrupt_id,
                            "report": {
                                "patient_id": "PAT-1001",
                                "patient_name": "Jane Doe",
                                "age": 35,
                                "primary_symptom": msg,
                                "vitals": {
                                    "temperature_f": 102.5,
                                    "oxygen_sat_pct": 91,
                                    "heart_rate_bpm": 105,
                                    "blood_pressure_sys": 145,
                                    "blood_pressure_dia": 90,
                                },
                            }
                        })
            except Exception:
                pass

        return {
            "status": "success",
            "count": len(pending_items),
            "agent_runtime_id": AGENT_RUNTIME_ID,
            "pending": pending_items
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/action/{session_id}")
async def submit_triage_decision(session_id: str, req: TriageActionRequest):
    """Resumes paused session on Agent Runtime with physician decision."""
    try:
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        access_token = credentials.token

        url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{AGENT_RUNTIME_ID}:streamQuery"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "class_method": "async_stream_query",
            "input": {
                "user_id": req.user_id,
                "session_id": session_id,
                "message": {
                    "role": "user",
                    "parts": [{
                        "function_response": {
                            "id": "doctor_review",
                            "name": "adk_request_input",
                            "response": {
                                "action": req.action,
                                "response": f"{req.action} - {req.notes}"
                            }
                        }
                    }]
                }
            }
        }

        res = requests.post(url, headers=headers, json=payload, timeout=60)
        return {
            "status": "success",
            "action": req.action,
            "agent_response": res.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

