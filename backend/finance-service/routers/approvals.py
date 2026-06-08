import uuid
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_role
from config import settings
from database import get_db
from models import ApprovalAction, FinanceApproval
from schemas import ApproveRequest, FinanceApprovalResponse, RejectRequest

router = APIRouter(prefix="/finance", tags=["finance"])


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
    user: dict = Depends(require_role("finance")),
    db: AsyncSession = Depends(get_db),
):
    requests_data: List[dict] = await _hr_get("/internal/onboarding?status=finance_review")

    request_ids = [uuid.UUID(r["id"]) for r in requests_data]
    approvals: dict[str, FinanceApprovalResponse] = {}

    if request_ids:
        result = await db.execute(
            select(FinanceApproval).where(FinanceApproval.onboarding_request_id.in_(request_ids))
        )
        for appr in result.scalars().all():
            approvals[str(appr.onboarding_request_id)] = FinanceApprovalResponse.model_validate(appr)

    return [
        {"onboarding_request": r, "existing_approval": approvals.get(r["id"])}
        for r in requests_data
    ]


@router.get("/approvals/{request_id}", response_model=List[FinanceApprovalResponse])
async def get_approvals(
    request_id: uuid.UUID,
    user: dict = Depends(require_role("finance")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FinanceApproval)
        .where(FinanceApproval.onboarding_request_id == request_id)
        .order_by(FinanceApproval.approved_at.desc())
    )
    return result.scalars().all()


@router.post("/approvals/{request_id}/approve", response_model=FinanceApprovalResponse)
async def approve(
    request_id: uuid.UUID,
    data: ApproveRequest,
    user: dict = Depends(require_role("finance")),
    db: AsyncSession = Depends(get_db),
):
    req_data = await _hr_get(f"/internal/onboarding/{request_id}")

    if req_data["status"] != "finance_review":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending finance review. Current status: {req_data['status']}",
        )

    approval = FinanceApproval(
        onboarding_request_id=request_id,
        notes=data.notes,
        action=ApprovalAction.approved,
        approved_by=uuid.UUID(user["id"]),
    )
    db.add(approval)
    await db.commit()

    await _hr_put_status(request_id, {"new_status": "it_provisioning"})

    await db.refresh(approval)
    return approval


@router.post("/approvals/{request_id}/reject", response_model=FinanceApprovalResponse)
async def reject(
    request_id: uuid.UUID,
    data: RejectRequest,
    user: dict = Depends(require_role("finance")),
    db: AsyncSession = Depends(get_db),
):
    req_data = await _hr_get(f"/internal/onboarding/{request_id}")

    if req_data["status"] != "finance_review":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending finance review. Current status: {req_data['status']}",
        )

    approval = FinanceApproval(
        onboarding_request_id=request_id,
        action=ApprovalAction.rejected,
        approved_by=uuid.UUID(user["id"]),
        rejection_reason=data.reason,
    )
    db.add(approval)
    await db.commit()

    await _hr_put_status(
        request_id,
        {
            "new_status": "needs_rework",
            "rejection_reason": data.reason,
            "rejected_by": user["id"],
        },
    )

    await db.refresh(approval)
    return approval
