# Patient Alerts
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database import query_all, query_one, execute
from app.dependencies import get_current_user
from app.sockets import sio

router = APIRouter(prefix="/api/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)])

ALERT_SELECT = """
    SELECT a.id, a.type, a.severity, a.location, a.confidence, a.status,
           a.created_at, a.resolved_at,
           p.id AS patient_id, p.slug, p.name AS patient_name
    FROM alerts a
    JOIN patients p ON p.id = a.patient_id
"""


def shape_alert(row: dict) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "severity": row["severity"],
        "location": row["location"],
        "confidence": row["confidence"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "resolvedAt": row["resolved_at"],
        "patient": {"id": row["patient_id"], "slug": row["slug"], "name": row["patient_name"]},
    }


@router.get("")
def list_alerts(status: str = "active"):
    """alerts.html 'Active Alerts' (pass ?status=active|resolved)"""
    rows = query_all(f"{ALERT_SELECT} WHERE a.status = %s ORDER BY a.created_at DESC", (status,))
    return [shape_alert(r) for r in rows]


@router.put("/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """alerts.html 'Resolve'/'Ignore' button"""
    _, row_count = execute(
        "UPDATE alerts SET status = 'resolved', resolved_at = NOW() WHERE id = %s AND status = 'active'",
        (alert_id,),
    )

    if row_count == 0:
        raise HTTPException(status_code=404, detail="Active alert not found.")

    alert = query_one(f"{ALERT_SELECT} WHERE a.id = %s", (alert_id,))

    execute(
        """INSERT INTO history_events (patient_id, event_type, title, description, icon_color)
           VALUES (%s, 'resolved', %s, 'No fall confirmed after caregiver review.', 'green')""",
        (alert["patient_id"], f"{alert['patient_name']} — Alert Resolved"),
    )

    await sio.emit("alert:resolved", shape_alert(alert))

    return {"success": True}


class CreateAlertRequest(BaseModel):
    patientSlug: str
    type: str
    severity: str
    location: str
    confidence: Optional[int] = None


@router.post("", status_code=201)
async def create_alert(body: CreateAlertRequest):
    """Manual alert creation from the caregiver app (rare; devices usually trigger these)"""
    patient = query_one("SELECT id, name FROM patients WHERE slug = %s", (body.patientSlug,))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    last_id, _ = execute(
        """INSERT INTO alerts (patient_id, type, severity, location, confidence, status)
           VALUES (%s, %s, %s, %s, %s, 'active')""",
        (patient["id"], body.type, body.severity, body.location, body.confidence),
    )

    alert = query_one(f"{ALERT_SELECT} WHERE a.id = %s", (last_id,))
    shaped = shape_alert(alert)

    await sio.emit("alert:new", shaped)

    return shaped
