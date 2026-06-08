from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine, Base
from routers.auth import router as auth_router
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()


app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)

app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-service"}
