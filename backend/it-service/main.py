from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import Base, engine
from routers.provisioning import router as it_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="IT Provisioning Service", version="1.0.0", lifespan=lifespan)

app.include_router(it_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "it-service"}
