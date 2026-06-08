from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import Base, engine
from routers.onboarding import internal_router, router as hr_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="HR Service", version="1.0.0", lifespan=lifespan)

app.include_router(hr_router)
app.include_router(internal_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hr-service"}
