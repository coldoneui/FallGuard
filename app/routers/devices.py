# API to Devices
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from app.database import query_all, query_one, execute
from app.dependencies import get_current_user, require_device_key
from app.sockets import sio

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", dependencies=[Depends(get_current_user)])
def list_devices():
    """settings.html 'Connected Devices' row"""
    rows = query_all(
        """SELECT d.id, d.device_name, d.connection_type, d.sensor_type,
                  d.battery_percent, d.is_online, d.last_seen_at,
                  p.slug AS patient_slug, p.name AS patient_name
           FROM devices d
           JOIN patients p ON p.id = d.patient_id"""
    )

    return [
        {
            "id": r["id"],
            "name": r["device_name"],
            "connectionType": r["connection_type"],
            "sensorType": r["sensor_type"],
            "batteryPercent": r["battery_percent"],
            "isOnline": bool(r["is_online"]),
            "lastSeenAt": r["last_seen_at"],
            "patient": {"slug": r["patient_slug"], "name": r["patient_name"]},
        }
        for r in rows
    ]


class TelemetryRequest(BaseModel):
    heartRate: Optional[int] = None
    fallDetected: bool = False
    nearFall: bool = False
    motion: Optional[str] = None  # 'walking' | 'resting' | 'still'
    batteryPercent: Optional[int] = None
    location: Optional[str] = None
    confidence: Optional[int] = None


STATUS_MAP = {
    "walking": "● Safe · Walking",
    "resting": "● Safe · Resting",
    "still": "● Safe · Still",
}


@router.post("/{device_name}/telemetry", dependencies=[Depends(require_device_key)])
async def ingest_telemetry(device_name: str, body: TelemetryRequest):
    """
    Called directly by the ESP32 firmware, authenticated with x-device-key
    (NOT a caregiver JWT - see app/dependencies.py -> require_device_key).

    This is what makes the app real-time: every reading is stored, and the
    relevant Socket.IO events are broadcast immediately so the caregiver
    dashboard updates without any polling or page refresh.
    """
    device = query_one(
        """SELECT d.id, d.patient_id, d.device_name AS name, p.slug, p.name AS patient_name, p.risk_level
           FROM devices d JOIN patients p ON p.id = d.patient_id
           WHERE d.device_name = %s""",
        (device_name,),
    )

    if not device:
        raise HTTPException(status_code=404, detail=f'No patient is linked to device "{device_name}".')

    # 1. Update device health (battery / online / last-seen)
    execute(
        """UPDATE devices SET battery_percent = COALESCE(%s, battery_percent), is_online = TRUE, last_seen_at = NOW()
           WHERE id = %s""",
        (body.batteryPercent, device["id"]),
    )
    await sio.emit("device:update", {
        "deviceName": device_name,
        "batteryPercent": body.batteryPercent,
        "isOnline": True,
    })

    # 2. Store heart rate reading and push it live
    if body.heartRate is not None:
        execute("INSERT INTO vitals (patient_id, heart_rate) VALUES (%s, %s)", (device["patient_id"], body.heartRate))
        await sio.emit("patient:vitals", {
            "patientSlug": device["slug"],
            "heartRate": body.heartRate,
            "recordedAt": datetime.now(timezone.utc).isoformat(),
        })

    # 3. Update activity/status text based on motion state
    if body.motion:
        status_text = STATUS_MAP.get(body.motion)
        execute(
            "UPDATE patients SET activity = %s, status_text = COALESCE(%s, status_text) WHERE id = %s",
            (body.motion.capitalize(), status_text, device["patient_id"]),
        )
        await sio.emit("patient:status", {
            "patientSlug": device["slug"],
            "activity": body.motion,
            "statusText": status_text,
        })

    # 4. Fall / near-fall detected -> create an alert + history event + high-priority push
    if body.fallDetected or body.nearFall:
        severity = "high" if body.fallDetected else "medium"
        alert_type = "Fall Detected" if body.fallDetected else "Near-fall detected"
        confidence = body.confidence if body.confidence is not None else (90 if body.fallDetected else 65)
        location = body.location or "Unknown"

        last_id, _ = execute(
            """INSERT INTO alerts (patient_id, type, severity, location, confidence, status)
               VALUES (%s, %s, %s, %s, %s, 'active')""",
            (device["patient_id"], alert_type, severity, location, confidence),
        )

        if body.fallDetected:
            execute(
                """UPDATE patients SET risk_level = 'High Risk', activity = 'Fall Detected', status_text = '● Fall Detected'
                   WHERE id = %s""",
                (device["patient_id"],),
            )

        description = (
            f"High impact fall detected in {location}."
            if body.fallDetected
            else f"Possible stumble detected in {location}."
        )

        execute(
            """INSERT INTO history_events (patient_id, event_type, title, description, icon_color)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                device["patient_id"],
                "fall" if body.fallDetected else "near_fall",
                f"{device['name']} — {alert_type}",
                description,
                "red" if body.fallDetected else "yellow",
            ),
        )

        await sio.emit("alert:new", {
            "id": last_id,
            "type": alert_type,
            "severity": severity,
            "confidence": confidence,
            "location": location,
            "patient": {"slug": device["slug"], "name": device["patient_name"]},
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })

    return {"success": True}
