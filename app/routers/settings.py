# Settings API
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database import query_one, execute
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("")
def get_settings(current_user: dict = Depends(get_current_user)):
    """settings.html toggle states"""
    row = query_one("SELECT * FROM user_settings WHERE user_id = %s", (current_user["id"],))
    if not row:
        raise HTTPException(status_code=404, detail="Settings not found for this user.")

    return {
        "fallAlerts": bool(row["fall_alerts"]),
        "smsAlerts": bool(row["sms_alerts"]),
        "soundAlerts": bool(row["sound_alerts"]),
        "darkMode": bool(row["dark_mode"]),
        "language": row["language"],
    }


class SettingsUpdateRequest(BaseModel):
    fallAlerts: Optional[bool] = None
    smsAlerts: Optional[bool] = None
    soundAlerts: Optional[bool] = None
    darkMode: Optional[bool] = None
    language: Optional[str] = None


@router.put("")
def update_settings(body: SettingsUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Save toggle changes from settings.html"""
    execute(
        """UPDATE user_settings SET
             fall_alerts = COALESCE(%s, fall_alerts),
             sms_alerts = COALESCE(%s, sms_alerts),
             sound_alerts = COALESCE(%s, sound_alerts),
             dark_mode = COALESCE(%s, dark_mode),
             language = COALESCE(%s, language)
           WHERE user_id = %s""",
        (body.fallAlerts, body.smsAlerts, body.soundAlerts, body.darkMode, body.language, current_user["id"]),
    )
    return {"success": True}
