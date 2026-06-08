import uuid
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, require_role
from config import settings
from database import get_db
from models import OnboardingRequest, OnboardingStatus
from schemas import OnboardingCreate, OnboardingResponse, OnboardingUpdate, StatusUpdateInternal

router = APIRouter(prefix="/hr", tags=["hr"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])


def _generate_fisa_de_post(employee_name: str, role: str, start_date: str, hardware_tier: str) -> str:
    return (
        f"FIȘA DE POST\n"
        f"{'=' * 40}\n\n"
        f"Nume angajat: {employee_name}\n"
        f"Funcție/Rol: {role}\n"
        f"Data începerii: {start_date}\n"
        f"Nivel hardware: {hardware_tier.capitalize()}\n\n"
        f"ATRIBUȚII ȘI RESPONSABILITĂȚI:\n"
        f"1. Îndeplinirea sarcinilor specifice postului de {role}\n"
        f"2. Respectarea regulamentului intern al companiei\n"
        f"3. Colaborarea cu echipa și departamentele conexe\n"
        f"4. Raportarea activității către managerul direct\n\n"
        f"CERINȚE:\n"
        f"- Competențe tehnice specifice rolului de {role}\n"
        f"- Abilități de comunicare și lucru în echipă\n"
        f"- Respectarea politicilor de securitate IT\n\n"
        f"RESURSE ALOCATE:\n"
        f"- Laptop: Configurație {hardware_tier.capitalize()}\n"
        f"- Acces sisteme: conform necesităților rolului\n\n"
        f"Generat automat la {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')} UTC"
    )


async def _call_notifier(event_data: dict) -> None:
    """Fire-and-forget notification. Never raises."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.NOTIFIER_SERVICE_URL}/internal/notify",
                json=event_data,
                headers={"X-Internal-Secret": settings.INTERNAL_SECRET},
            )
    except Exception:
        pass


@router.post("/onboarding", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
async def create_onboarding(
    data: OnboardingCreate,
    user: dict = Depends(require_role("hr")),
    db: AsyncSession = Depends(get_db),
):
    fisa = _generate_fisa_de_post(data.employee_name, data.role, data.start_date, data.hardware_tier.value)

    request = OnboardingRequest(
        employee_name=data.employee_name,
        role=data.role,
        start_date=data.start_date,
        hardware_tier=data.hardware_tier,
        status=OnboardingStatus.manager_review,
        fisa_de_post=fisa,
        created_by=uuid.UUID(user["id"]),
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)

    await _call_notifier(
        {
            "event": "status_update",
            "onboarding_request_id": str(request.id),
            "employee_name": request.employee_name,
            "old_status": "initiated",
            "new_status": "manager_review",
            "target_roles": ["manager", "hr"],
            "message": f"New onboarding request for {request.employee_name} is pending manager review",
            "rejection_reason": None,
        }
    )

    return request


@router.get("/onboarding", response_model=List[OnboardingResponse])
async def list_onboarding(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = user["role"]

    status_filter = {
        "manager": OnboardingStatus.manager_review,
        "finance": OnboardingStatus.finance_review,
        "it": OnboardingStatus.it_provisioning,
    }

    if role == "hr":
        stmt = (
            select(OnboardingRequest)
            .where(OnboardingRequest.created_by == uuid.UUID(user["id"]))
            .order_by(OnboardingRequest.created_at.desc())
        )
    elif role in status_filter:
        stmt = (
            select(OnboardingRequest)
            .where(OnboardingRequest.status == status_filter[role])
            .order_by(OnboardingRequest.created_at.desc())
        )
    else:
        raise HTTPException(status_code=403, detail="Unknown role")

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/onboarding/{request_id}", response_model=OnboardingResponse)
async def get_onboarding(
    request_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Onboarding request not found")

    if user["role"] == "hr" and str(req.created_by) != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return req


@router.put("/onboarding/{request_id}", response_model=OnboardingResponse)
async def update_onboarding(
    request_id: uuid.UUID,
    data: OnboardingUpdate,
    user: dict = Depends(require_role("hr")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Onboarding request not found")

    if str(req.created_by) != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if req.status != OnboardingStatus.needs_rework:
        raise HTTPException(status_code=400, detail="Only requests in 'needs_rework' status can be edited")

    if data.employee_name is not None:
        req.employee_name = data.employee_name
    if data.role is not None:
        req.role = data.role
    if data.start_date is not None:
        req.start_date = data.start_date
    if data.hardware_tier is not None:
        req.hardware_tier = data.hardware_tier

    req.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(req)
    return req


@router.post("/onboarding/{request_id}/resubmit", response_model=OnboardingResponse)
async def resubmit_onboarding(
    request_id: uuid.UUID,
    user: dict = Depends(require_role("hr")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Onboarding request not found")

    if str(req.created_by) != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if req.status != OnboardingStatus.needs_rework:
        raise HTTPException(status_code=400, detail="Only requests in 'needs_rework' status can be resubmitted")

    old_status = req.status.value

    req.fisa_de_post = _generate_fisa_de_post(req.employee_name, req.role, req.start_date, req.hardware_tier.value)
    req.status = OnboardingStatus.manager_review
    req.rejection_reason = None
    req.rejected_by = None
    req.rejected_at = None
    req.submission_count += 1
    req.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(req)

    await _call_notifier(
        {
            "event": "status_update",
            "onboarding_request_id": str(req.id),
            "employee_name": req.employee_name,
            "old_status": old_status,
            "new_status": "manager_review",
            "target_roles": ["manager", "hr"],
            "message": f"Onboarding for {req.employee_name} has been resubmitted (attempt #{req.submission_count})",
            "rejection_reason": None,
        }
    )

    return req


@internal_router.get("/onboarding", response_model=List[OnboardingResponse])
async def internal_list_by_status(
    status: str,
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
):
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Invalid internal secret")

    try:
        status_enum = OnboardingStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status value: {status}")

    result = await db.execute(
        select(OnboardingRequest)
        .where(OnboardingRequest.status == status_enum)
        .order_by(OnboardingRequest.created_at.desc())
    )
    return result.scalars().all()


@internal_router.get("/onboarding/{request_id}", response_model=OnboardingResponse)
async def internal_get_onboarding(
    request_id: uuid.UUID,
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
):
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Invalid internal secret")

    result = await db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    return req


@internal_router.put("/onboarding/{request_id}/status")
async def internal_update_status(
    request_id: uuid.UUID,
    data: StatusUpdateInternal,
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
):
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Invalid internal secret")

    result = await db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Onboarding request not found")

    old_status = req.status.value
    req.status = data.new_status
    req.updated_at = datetime.utcnow()

    if data.rejection_reason:
        req.rejection_reason = data.rejection_reason
        req.rejected_by = uuid.UUID(data.rejected_by) if data.rejected_by else None
        req.rejected_at = datetime.utcnow()
    else:
        req.rejection_reason = None
        req.rejected_by = None
        req.rejected_at = None

    await db.commit()
    await db.refresh(req)

    target_roles = ["hr"]
    notify_map = {
        "manager_review": "manager",
        "finance_review": "finance",
        "it_provisioning": "it",
    }
    if data.new_status.value in notify_map:
        target_roles.append(notify_map[data.new_status.value])

    await _call_notifier(
        {
            "event": "status_update",
            "onboarding_request_id": str(req.id),
            "employee_name": req.employee_name,
            "old_status": old_status,
            "new_status": data.new_status.value,
            "target_roles": target_roles,
            "message": f"Onboarding for {req.employee_name} moved from '{old_status}' to '{data.new_status.value}'",
            "rejection_reason": data.rejection_reason,
        }
    )

    return {"status": "updated", "new_status": data.new_status.value}
