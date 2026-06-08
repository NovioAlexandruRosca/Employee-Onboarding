from datetime import datetime, timezone
from typing import Dict, List

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from config import settings
from schemas import NotifyPayload
import logging

logger = logging.getLogger("notifier")
logger.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

VALID_ROLES = {"hr", "manager", "finance", "it"}


class ConnectionManager:

    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {role: [] for role in VALID_ROLES}

    async def connect(self, websocket: WebSocket, role: str) -> None:
        await websocket.accept()
        self._connections[role].append(websocket)

    def disconnect(self, websocket: WebSocket, role: str) -> None:
        connections = self._connections.get(role, [])
        if websocket in connections:
            connections.remove(websocket)

    async def broadcast_to_roles(self, roles: List[str], message: dict) -> None:
        logger.info(f"Broadcast started | roles={roles} | event={message.get('event')}")

        total_sent = 0
        total_failed = 0

        for role in roles:
            stale: List[WebSocket] = []

            for ws in self._connections.get(role, []):
                try:
                    await ws.send_json(message)
                    total_sent += 1
                except Exception as e:
                    logger.warning(f"Failed sending to role={role}: {e}")
                    stale.append(ws)
                    total_failed += 1

            for ws in stale:
                self._connections[role].remove(ws)

        logger.info(
            f"Broadcast finished | roles={roles} | sent={total_sent} | failed={total_failed}"
        )

    def connection_counts(self) -> Dict[str, int]:
        return {role: len(conns) for role, conns in self._connections.items()}


manager = ConnectionManager()

app = FastAPI(title="Notifier Service", version="1.0.0")


def _validate_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        payload = _validate_token(token)
        role: str = payload.get("role", "")
        user_id: str = payload.get("sub", "")
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    if role not in VALID_ROLES:
        await websocket.close(code=1008, reason="Unknown role")
        return

    await manager.connect(websocket, role)

    await websocket.send_json(
        {
            "event": "connected",
            "message": f"Listening for updates as '{role}'",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, role)
    except Exception:
        manager.disconnect(websocket, role)


@app.post("/internal/notify", status_code=200)
async def internal_notify(
    payload: NotifyPayload,
    x_internal_secret: str = Header(None, alias="X-Internal-Secret"),
):
    if x_internal_secret != settings.INTERNAL_SECRET:
        logger.warning("Rejected internal notify due to invalid secret")
        raise HTTPException(status_code=403, detail="Invalid internal secret")

    logger.info(
        f"Internal notify received | event={payload.event} | "
        f"request_id={payload.onboarding_request_id} | roles={payload.target_roles}"
    )

    message = {
        "event": payload.event,
        "onboarding_request_id": payload.onboarding_request_id,
        "employee_name": payload.employee_name,
        "old_status": payload.old_status,
        "new_status": payload.new_status,
        "message": payload.message,
        "rejection_reason": payload.rejection_reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await manager.broadcast_to_roles(payload.target_roles, message)

    logger.info(
        f"Internal notify completed | request_id={payload.onboarding_request_id}"
    )

    return {"status": "notified", "target_roles": payload.target_roles}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "notifier-service",
        "active_connections": manager.connection_counts(),
    }
