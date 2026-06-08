import uuid
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_role
from config import settings
from database import get_db
from models import ITProvision, ProvisionAction
from schemas import CompleteProvisionRequest, ITProvisionResponse, RejectRequest

router = APIRouter(prefix="/it", tags=["it"])


async def _hr_get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{settings.HR_SERVICE_URL}{path}",
            headers={"X-Internal-Secret": settings.INTERNAL_SECRET},
        )
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="HR service error")
    return resp.json()


async def _hr_put_status(request_id: uuid.UUID, payload: dict) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.put(
            f"{settings.HR_SERVICE_URL}/internal/onboarding/{request_id}/status",
            json=payload,
            headers={"X-Internal-Secret": settings.INTERNAL_SECRET},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to update onboarding status in HR service")


@router.get("/pending")
async def get_pending(
    user: dict = Depends(require_role("it")),
    db: AsyncSession = Depends(get_db),
):
    requests_data: List[dict] = await _hr_get("/internal/onboarding?status=it_provisioning")

    request_ids = [uuid.UUID(r["id"]) for r in requests_data]
    provisions: dict[str, ITProvisionResponse] = {}

    if request_ids:
        result = await db.execute(
            select(ITProvision).where(ITProvision.onboarding_request_id.in_(request_ids))
        )
        for prov in result.scalars().all():
            provisions[str(prov.onboarding_request_id)] = ITProvisionResponse.model_validate(prov)

    return [
        {"onboarding_request": r, "existing_provision": provisions.get(r["id"])}
        for r in requests_data
    ]


@router.get("/provisions/{request_id}", response_model=List[ITProvisionResponse])
async def get_provisions(
    request_id: uuid.UUID,
    user: dict = Depends(require_role("it")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ITProvision)
        .where(ITProvision.onboarding_request_id == request_id)
        .order_by(ITProvision.provisioned_at.desc())
    )
    return result.scalars().all()


@router.post("/provisions/{request_id}/complete", response_model=ITProvisionResponse)
async def complete_provision(
    request_id: uuid.UUID,
    data: CompleteProvisionRequest,
    user: dict = Depends(require_role("it")),
    db: AsyncSession = Depends(get_db),
):
    req_data = await _hr_get(f"/internal/onboarding/{request_id}")

    if req_data["status"] != "it_provisioning":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending IT provisioning. Current status: {req_data['status']}",
        )

    provision = ITProvision(
        onboarding_request_id=request_id,
        company_email=data.company_email,
        account_credentials=data.account_credentials,
        laptop_config=data.laptop_config,
        action=ProvisionAction.completed,
        provisioned_by=uuid.UUID(user["id"]),
    )
    db.add(provision)
    await db.commit()

    await _hr_put_status(request_id, {"new_status": "completed"})

    await db.refresh(provision)
    return provision


@router.post("/provisions/{request_id}/reject", response_model=ITProvisionResponse)
async def reject_provision(
    request_id: uuid.UUID,
    data: RejectRequest,
    user: dict = Depends(require_role("it")),
    db: AsyncSession = Depends(get_db),
):
    req_data = await _hr_get(f"/internal/onboarding/{request_id}")

    if req_data["status"] != "it_provisioning":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending IT provisioning. Current status: {req_data['status']}",
        )

    provision = ITProvision(
        onboarding_request_id=request_id,
        action=ProvisionAction.rejected,
        provisioned_by=uuid.UUID(user["id"]),
        rejection_reason=data.reason,
    )
    db.add(provision)
    await db.commit()

    await _hr_put_status(
        request_id,
        {
            "new_status": "needs_rework",
            "rejection_reason": data.reason,
            "rejected_by": user["id"],
        },
    )

    await db.refresh(provision)
    return provision
