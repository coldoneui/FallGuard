# Patient Query
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database import query_all, query_one, execute
from app.dependencies import get_current_user
from app.sockets import sio

router = APIRouter(prefix="/api/patients", tags=["patients"], dependencies=[Depends(get_current_user)])

PATIENT_SELECT = """
    SELECT
        p.id, p.slug, p.name, p.initials, p.age, p.room,
        p.risk_level, p.activity, p.status_text, p.avatar_color,
        d.id AS device_id, d.device_name, d.connection_type, d.sensor_type,
        d.battery_percent, d.is_online, d.last_seen_at,
        v.heart_rate, v.recorded_at AS heart_rate_recorded_at
    FROM patients p
    LEFT JOIN devices d ON d.patient_id = p.id
    LEFT JOIN vitals v ON v.id = (
        SELECT id FROM vitals WHERE patient_id = p.id ORDER BY recorded_at DESC LIMIT 1
    )
"""


def shape_patient(row: dict) -> dict:
    device = None
    if row.get("device_id"):
        device = {
            "id": row["device_id"],
            "name": row["device_name"],
            "connectionType": row["connection_type"],
            "sensorType": row["sensor_type"],
            "batteryPercent": row["battery_percent"],
            "isOnline": bool(row["is_online"]),
            "lastSeenAt": row["last_seen_at"],
        }

    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "initials": row["initials"],
        "age": row["age"],
        "room": row["room"],
        "riskLevel": row["risk_level"],
        "activity": row["activity"],
        "statusText": row["status_text"],
        "avatarColor": row["avatar_color"],
        "heartRate": row["heart_rate"],
        "heartRateRecordedAt": row["heart_rate_recorded_at"],
        "device": device,
    }


@router.get("")
def list_patients():
    """index.html cards + patients.html list"""
    rows = query_all(PATIENT_SELECT)
    return [shape_patient(r) for r in rows]


@router.get("/dashboard/stats")
def get_dashboard_stats():
    """index.html 'Quick Stats' card"""
    fall_events = query_one("SELECT COUNT(*) AS c FROM history_events WHERE event_type = 'fall'")["c"]
    total_patients = query_one("SELECT COUNT(*) AS c FROM patients")["c"]
    safe_patients = query_one("SELECT COUNT(*) AS c FROM patients WHERE risk_level = 'Stable'")["c"]
    alerts_sent = query_one("SELECT COUNT(*) AS c FROM alerts")["c"]

    return {
        "fallEvents": fall_events,
        "patientsSafe": f"{safe_patients}/{total_patients}",
        "avgResponseMinutes": 1.8,  # placeholder until response-time tracking is added
        "alertsSent": alerts_sent,
    }


@router.get("/{slug}")
def get_patient(slug: str):
    """patient-info.html (slug = pete / ana / ben)"""
    row = query_one(f"{PATIENT_SELECT} WHERE p.slug = %s", (slug,))
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found.")

    patient = shape_patient(row)

    recent_activity = query_all(
        """SELECT event_type, title, description, icon_color, created_at
           FROM history_events WHERE patient_id = %s ORDER BY created_at DESC LIMIT 5""",
        (patient["id"],),
    )

    return {**patient, "recentActivity": recent_activity}


class PatientUpdateRequest(BaseModel):
    riskLevel: Optional[str] = None
    activity: Optional[str] = None
    statusText: Optional[str] = None
    room: Optional[str] = None


@router.put("/{slug}")
async def update_patient(slug: str, body: PatientUpdateRequest):
    patient = query_one("SELECT id FROM patients WHERE slug = %s", (slug,))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    execute(
        """UPDATE patients SET
             risk_level = COALESCE(%s, risk_level),
             activity = COALESCE(%s, activity),
             status_text = COALESCE(%s, status_text),
             room = COALESCE(%s, room)
           WHERE id = %s""",
        (body.riskLevel, body.activity, body.statusText, body.room, patient["id"]),
    )

    await sio.emit("patient:update", {
        "patientId": patient["id"],
        "riskLevel": body.riskLevel,
        "activity": body.activity,
        "statusText": body.statusText,
        "room": body.room,
    })

    return {"success": True}
