# Python Dependencies
import jwt
from fastapi import Header, HTTPException, status
from app.security import decode_access_token
from app.config import settings


def get_current_user(authorization: str = Header(default=None)) -> dict:
    """Protects caregiver routes. Expects: Authorization: Bearer <token>"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header.")

    token = authorization.split(" ", 1)[1]

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid token, please log in again.")

    return payload  # contains at least {"id": ..., "email": ...}


def require_device_key(x_device_key: str = Header(default=None)) -> None:
    """Protects the device-ingestion endpoint. Expects: x-device-key: <DEVICE_API_KEY>"""
    if not x_device_key or x_device_key != settings.DEVICE_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing device key.")
