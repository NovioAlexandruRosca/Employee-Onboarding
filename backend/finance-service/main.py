from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import Base, engine
from routers.approvals import router as finance_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Finance Service", version="1.0.0", lifespan=lifespan)

app.include_router(finance_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "finance-service"}
