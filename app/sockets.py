import socketio
from app.config import settings

# Same wire protocol as Node's socket.io, so your existing frontend
# <script src=".../socket.io.min.js"> client code needs zero changes.
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.CLIENT_ORIGIN if settings.CLIENT_ORIGIN != "*" else "*",
)


@sio.event
async def connect(sid, environ):
    print(f"Socket connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Socket disconnected: {sid}")
