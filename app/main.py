# API
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.sockets import sio
from app.routers import auth, patients, alerts, history, settings as settings_router, devices

fastapi_app = FastAPI(title="FallGuard API")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CLIENT_ORIGIN] if settings.CLIENT_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.get("/api/health")
def health():
    return {"status": "ok"}


fastapi_app.include_router(auth.router)
fastapi_app.include_router(patients.router)
fastapi_app.include_router(alerts.router)
fastapi_app.include_router(history.router)
fastapi_app.include_router(settings_router.router)
fastapi_app.include_router(devices.router)

# Combine the FastAPI app with the Socket.IO server into a single ASGI app.
# REST calls (/api/...) go to FastAPI; Socket.IO traffic (/socket.io/...) is
# handled by python-socketio. Run this with: uvicorn app.main:app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
