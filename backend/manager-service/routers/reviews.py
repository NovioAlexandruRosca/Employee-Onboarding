import uuid
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_role
from config import settings
from database import get_db
from models import ManagerReview, ReviewAction
from schemas import ApproveRequest, ManagerReviewResponse, RejectRequest

router = APIRouter(prefix="/manager", tags=["manager"])


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
    user: dict = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    requests_data: List[dict] = await _hr_get("/internal/onboarding?status=manager_review")

    request_ids = [uuid.UUID(r["id"]) for r in requests_data]
    reviews: dict[str, ManagerReviewResponse] = {}

    if request_ids:
        result = await db.execute(
            select(ManagerReview).where(ManagerReview.onboarding_request_id.in_(request_ids))
        )
        for rev in result.scalars().all():
            reviews[str(rev.onboarding_request_id)] = ManagerReviewResponse.model_validate(rev)

    return [
        {"onboarding_request": r, "existing_review": reviews.get(r["id"])}
        for r in requests_data
    ]


@router.get("/reviews/{request_id}", response_model=List[ManagerReviewResponse])
async def get_reviews(
    request_id: uuid.UUID,
    user: dict = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ManagerReview)
        .where(ManagerReview.onboarding_request_id == request_id)
        .order_by(ManagerReview.reviewed_at.desc())
    )
    return result.scalars().all()


@router.post("/reviews/{request_id}/approve", response_model=ManagerReviewResponse)
async def approve_review(
    request_id: uuid.UUID,
    data: ApproveRequest,
    user: dict = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    req_data = await _hr_get(f"/internal/onboarding/{request_id}")

    if req_data["status"] != "manager_review":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending manager review. Current status: {req_data['status']}",
        )

    review = ManagerReview(
        onboarding_request_id=request_id,
        fisa_de_post_notes=data.notes,
        action=ReviewAction.approved,
        reviewed_by=uuid.UUID(user["id"]),
    )
    db.add(review)
    await db.commit()

    next_status = "finance_review" if req_data["hardware_tier"] == "premium" else "it_provisioning"
    await _hr_put_status(request_id, {"new_status": next_status})

    await db.refresh(review)
    return review


@router.post("/reviews/{request_id}/reject", response_model=ManagerReviewResponse)
async def reject_review(
    request_id: uuid.UUID,
    data: RejectRequest,
    user: dict = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    req_data = await _hr_get(f"/internal/onboarding/{request_id}")

    if req_data["status"] != "manager_review":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending manager review. Current status: {req_data['status']}",
        )

    review = ManagerReview(
        onboarding_request_id=request_id,
        action=ReviewAction.rejected,
        reviewed_by=uuid.UUID(user["id"]),
        rejection_reason=data.reason,
    )
    db.add(review)
    await db.commit()

    await _hr_put_status(
        request_id,
        {
            "new_status": "needs_rework",
            "rejection_reason": data.reason,
            "rejected_by": user["id"],
        },
    )

    await db.refresh(review)
    return review
