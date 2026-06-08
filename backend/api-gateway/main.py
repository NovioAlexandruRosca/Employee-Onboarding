import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import websockets
import websockets.exceptions
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from fastapi.middleware.cors import CORSMiddleware
from config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("api-gateway")

# Tuple of path prefixes that do NOT require JWT authentication
NO_AUTH_PREFIXES = ("/auth/",)

# This contains the urls to the microservices, this would be replaced by a service discovery
# module either from the cloud provider or a custom one
SERVICE_MAP = {
    "/auth": settings.AUTH_SERVICE_URL,
    "/hr": settings.HR_SERVICE_URL,
    "/manager": settings.MANAGER_SERVICE_URL,
    "/finance": settings.FINANCE_SERVICE_URL,
    "/it": settings.IT_SERVICE_URL,
    "/notify": settings.NOTIFIER_SERVICE_URL,
}

# Global HTTP client instance to be used across requests, initialized in lifespan
http_client: Optional[httpx.AsyncClient] = None

# Creates a FastAPI app with a lifespan that
# when the app starts, it initializes a global http_client that can be used across requests
# When the app shuts down, it ensures that the http_client is properly closed to free up resources
@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await http_client.aclose()


app = FastAPI(title="API Gateway", version="1.0.0", lifespan=lifespan)

# This is for dev only - in production, CORS should be configured more restrictively based on the
# actual frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# There are 2 types of headers
# HOP BY HOP 
# END TO END
# the hop by hope are meant to be sent only from one node to another one not on the enitre flow
HOP_BY_HOP = frozenset(
    {"host", "content-length", "transfer-encoding", "connection", "keep-alive", "upgrade", "proxy-authorization"}
)


def _validate_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _requires_auth(path: str) -> bool:
    for prefix in NO_AUTH_PREFIXES:
        if path.startswith(prefix):
            return False
    return True


def _get_target_url(path: str) -> str:
    for prefix, base_url in SERVICE_MAP.items():
        if path.startswith(prefix):
            return f"{base_url}{path}"
    raise HTTPException(status_code=404, detail=f"No route configured for: {path}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


# This is a websocket proxy endpoint that accepts websockets cons from clients and 
# forwards them to the notifier service.
@app.websocket("/ws")
async def websocket_proxy(websocket: WebSocket, token: str = Query(None)):
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        _validate_token(token)
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    await websocket.accept()

    notifier_url = f"{settings.NOTIFIER_SERVICE_WS_URL}/ws?token={token}"

    try:
        async with websockets.connect(notifier_url) as backend_ws:
            # there are 2 tasks, 
            # one for forwarding messages from the backend to the client
            # and another for forwarding messages from the client to the backend
            # we need to be able to handle both text and binary as this is what ws supports
            # I haven't decided initially on what exactly the notifier service will send 
            # so i decided to support both
            async def backend_to_client():
                try:
                    async for message in backend_ws:
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except (websockets.exceptions.ConnectionClosed, WebSocketDisconnect):
                    pass

            async def client_to_backend():
                try:
                    async for message in websocket.iter_text():
                        await backend_ws.send(message)
                except (WebSocketDisconnect, Exception):
                    pass

            # two tasks that run concurrently, 
            # if one of them finishes (either client disconnects or backend disconnects),
            # we cancel the other one and close the connection
            tasks = [
                asyncio.ensure_future(backend_to_client()),
                asyncio.ensure_future(client_to_backend()),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()

    # Some dedicated logging for websocket errors to help with debugging would be added in a more finished version
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy(request: Request, path: str):
    
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    logger.info(f"Query params: {dict(request.query_params)}")
    
    full_path = f"/{path}"

    user_id = user_role = user_email = ""

    if _requires_auth(full_path):
        logger.info(f"Auth required for path: {full_path}")

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing Authorization header")
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ", 1)[1]

        try:
            payload = _validate_token(token)
            logger.info(f"Token valid for user: {payload.get('sub')}")
        except HTTPException:
            logger.warning("Invalid token")
            raise

        user_id = payload.get("sub", "")
        user_role = payload.get("role", "")
        user_email = payload.get("email", "")
    else:
        logger.info(f"No auth required for path: {full_path}")

    target_url = _get_target_url(full_path)
    logger.info(f"Routing: {full_path} -> {target_url}")

    forward_headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}

    if user_id:
        forward_headers["X-User-Id"] = user_id
        forward_headers["X-User-Role"] = user_role
        forward_headers["X-User-Email"] = user_email

    body = await request.body()


    logger.info(f"Forwarding {request.method} {target_url}")
    logger.info(f"Forward headers: {forward_headers}")
    try:
        response = await http_client.request(
            method=request.method,
            url=target_url,
            headers=forward_headers,
            content=body,
            params=dict(request.query_params),
            follow_redirects=False,
        )
    except httpx.ConnectError as e:
        logger.error(f"Upstream connect error: {target_url} | {e}")
        raise HTTPException(status_code=503, detail="Upstream service unavailable")
    except httpx.TimeoutException as e:
        logger.error(f"Upstream timeout: {target_url} | {e}")
        raise HTTPException(status_code=504, detail="Upstream service timeout")

    response_headers = {
        k: v
        for k, v in response.headers.items()
        if k.lower() not in {"transfer-encoding", "connection", "content-encoding"}
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )
