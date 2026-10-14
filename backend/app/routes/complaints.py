"""
GhostWatt — routes/complaints.py
Endpoints for student water complaints, administrative lifecycle management,
file uploads, audit history, and admin notification logging.

SPEC §10 & Prompt Requirements:
- POST /complaints: multipart form data (building, location, category, description, optional photo).
- Validates file type and size (<= 5MB), saves to uploads/complaints/.
- Generates unique complaint code (e.g. WC-0001).
- Lifecycle: Submitted, Acknowledged, Assigned, In Progress, Resolved, Reopened.
- Every state change logged to complaint_history.
- GET /complaints: students see only their own; admins see all with filters, overdue flag,
  and frequently affected locations.
- GET /complaints/{id}: students cannot read another student's complaint (403 Forbidden).
- PATCH /complaints/{id} (Admin only): acknowledge, assign, add notes, update status.
- Admin notification recorded on new complaint submission (no external service).
"""
from datetime import datetime, timezone
import os
from typing import Any, List, Optional
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings as app_config
from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.schemas.complaints import (
    AdminNotificationItem,
    AdminNotificationListResponse,
    ComplaintHistoryItem,
    ComplaintListResponse,
    ComplaintPatch,
    ComplaintReopen,
    ComplaintResponse,
    FrequentlyAffectedLocation,
)

router = APIRouter()

# Directory for uploaded complaint photographs (absolute path under backend/uploads)
UPLOAD_DIR = str(app_config.uploads_path / "complaints")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Water issues + the electricity / facility issues the student form also offers.
VALID_CATEGORIES = {
    "leaking_tap",
    "broken_pipe",
    "overflowing_tank",
    "low_pressure",
    "general_wastage",
    "lights_left_on",
    "ac_running",
    "electrical_damage",
    "appliance_left_on",
    "other",
}
# Friendly aliases sent by the UI -> stored value
CATEGORY_ALIASES = {"water_wastage": "general_wastage"}


def _looks_like_image(ext: str, head: bytes) -> bool:
    """Cheap magic-byte check so a renamed script/HTML file is not stored as an image."""
    if ext in (".jpg", ".jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == ".gif":
        return head.startswith((b"GIF87a", b"GIF89a"))
    if ext == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return False

VALID_STATUS_LIFECYCLE = {
    "submitted": {"acknowledged", "assigned", "in_progress", "resolved"},
    "acknowledged": {"assigned", "in_progress", "resolved"},
    "assigned": {"in_progress", "resolved", "acknowledged"},
    "in_progress": {"resolved", "assigned"},
    "resolved": {"reopened"},
    "reopened": {"acknowledged", "assigned", "in_progress", "resolved"},
}


def _format_complaint(c: models.Complaint, db: Session) -> ComplaintResponse:
    """Format Complaint DB model with user info, overdue calculation, and history."""
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    age_hours = (now_utc - c.created_at).total_seconds() / 3600.0 if c.created_at else 0.0
    is_overdue = (c.status != "resolved") and (age_hours > 48.0)

    # Resolve student and assignee emails
    student_user = db.query(models.User).filter(models.User.id == c.student_id).first()
    assignee_user = (
        db.query(models.User).filter(models.User.id == c.assigned_to).first()
        if c.assigned_to
        else None
    )

    history_items = []
    history_records: Any = getattr(c, "history", None)
    if history_records:
        for h in sorted(history_records, key=lambda x: getattr(x, "changed_at", None) or datetime.min):
            changed_user = (
                db.query(models.User).filter(models.User.id == h.changed_by).first()
                if h.changed_by
                else None
            )
            history_items.append(
                ComplaintHistoryItem(
                    id=h.id,
                    complaint_id=h.complaint_id,
                    changed_by=h.changed_by,
                    changed_by_email=changed_user.email if changed_user else None,
                    old_status=h.old_status,
                    new_status=h.new_status,
                    note=h.note or "",
                    changed_at=h.changed_at.isoformat() if h.changed_at else "",
                )
            )

    return ComplaintResponse(
        id=c.id,
        complaint_code=c.complaint_code,
        student_id=c.student_id,
        student_email=student_user.email if student_user else None,
        student_username=student_user.username if student_user else None,
        building=c.building,
        location_detail=c.location_detail,
        category=c.category,
        description=c.description,
        attachment_path=c.attachment_path,
        assigned_to=c.assigned_to,
        assigned_to_email=assignee_user.email if assignee_user else None,
        status=c.status,
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
        resolution_notes=c.resolution_notes or "",
        is_overdue=is_overdue,
        title=((c.description or "").split("\n", 1)[0][:80] or c.category.replace("_", " ").title()),
        place=f"{c.building} - {c.location_detail}" if c.location_detail else c.building,
        image_url=f"/uploads/complaints/{os.path.basename(c.attachment_path)}" if c.attachment_path else None,
        history=history_items,
        data_source="simulated",
    )


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a water or facility complaint (Multipart form data)",
)
async def submit_complaint(
    building: Optional[str] = Form(None, description="Campus building (e.g. Block C, Block A)"),
    location: Optional[str] = Form(None, description="Location detail"),
    location_detail: Optional[str] = Form(None, description="Location detail alternative"),
    title: Optional[str] = Form(None, description="Short complaint title"),
    category: str = Form(..., description="leaking_tap | broken_pipe | overflowing_tank | low_pressure | general_wastage"),
    description: Optional[str] = Form(None, description="Detailed description of the water wastage issue"),
    photo: Optional[UploadFile] = File(None, description="Optional photographic evidence"),
    image: Optional[UploadFile] = File(None, description="Optional image upload (frontend alias)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Submit a student complaint:
    1. Validates category, building, and location strings.
    2. Validates optional uploaded image type and <= 5MB file size.
    3. Saves photo to uploads/complaints/.
    4. Generates unique complaint code (e.g. WC-0001).
    5. Creates complaint in 'submitted' status and logs initial complaint_history entry.
    6. Creates an internal admin notification record.
    """
    actual_photo = photo if (photo and photo.filename) else image
    title_in, desc_in = (title or "").strip(), (description or "").strip()
    # Keep BOTH: the first line is the short title, the rest is the longer description.
    actual_desc = f"{title_in}\n{desc_in}" if title_in and desc_in and title_in != desc_in else (desc_in or title_in)

    loc = (location or location_detail or "").strip()
    if not loc and building and building.strip():
        loc = building.strip()
    if not loc:
        raise HTTPException(
            status_code=422,
            detail="Please tell us where the issue is (building / exact location).",
        )
    bldg = (building or "").strip() or (loc.split("-")[0].strip() if "-" in loc else "Campus")

    if len((actual_desc or "").strip()) < 3:
        raise HTTPException(
            status_code=422,
            detail="Please add a short title or description of the issue.",
        )
    if len(actual_desc) > 1000 or len(loc) > 200 or len(bldg) > 50:
        raise HTTPException(
            status_code=422,
            detail="Description (max 1000), location (max 200) or building (max 50) is too long.",
        )

    cat_clean = category.strip().lower().replace(" ", "_").replace("-", "_")
    cat_clean = CATEGORY_ALIASES.get(cat_clean, cat_clean)
    if cat_clean not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category '{category}'. Must be one of: {sorted(VALID_CATEGORIES)}",
        )

    saved_attachment_path = None
    if actual_photo and actual_photo.filename:
        # Validate extension
        _, ext = os.path.splitext(actual_photo.filename)
        ext_lower = ext.lower()
        if ext_lower not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{ext}'. Allowed image formats: {sorted(ALLOWED_EXTENSIONS)}",
            )

        # Read at most limit+1 bytes so an oversized upload is never fully loaded into memory
        content = await actual_photo.read(MAX_FILE_SIZE_BYTES + 1)
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File exceeds maximum allowed size of 5 MB",
            )
        if not _looks_like_image(ext_lower, content[:16]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid JPG, PNG, GIF or WEBP image.",
            )

        # Save to disk under a server-generated name (never trust the client's filename)
        safe_filename = f"{uuid.uuid4().hex}{ext_lower}"
        disk_path = os.path.join(UPLOAD_DIR, safe_filename)
        with open(disk_path, "wb") as f:
            f.write(content)

        saved_attachment_path = f"uploads/complaints/{safe_filename}"

    # Generate unique complaint code: WC-0001, WC-0002, etc.
    count = db.query(models.Complaint).count()
    candidate_num = count + 1
    while True:
        code_candidate = f"WC-{candidate_num:04d}"
        exists = db.query(models.Complaint).filter(models.Complaint.complaint_code == code_candidate).first()
        if not exists:
            code = code_candidate
            break
        candidate_num += 1

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    complaint = models.Complaint(
        complaint_code=code,
        student_id=current_user.id,
        building=bldg.strip(),
        location_detail=loc.strip(),
        category=cat_clean,
        description=actual_desc.strip(),
        attachment_path=saved_attachment_path,
        assigned_to=None,
        status="submitted",
        created_at=now,
        updated_at=now,
        resolution_notes="",
    )
    db.add(complaint)
    db.flush()

    # Log initial entry in complaint_history
    history_entry = models.ComplaintHistory(
        complaint_id=complaint.id,
        changed_by=current_user.id,
        old_status=None,
        new_status="submitted",
        note="Complaint submitted by student",
        changed_at=now,
    )
    db.add(history_entry)

    # Record internal admin notification
    notification = models.AdminNotification(
        title=f"New Complaint: {complaint.complaint_code}",
        message=f"Student {current_user.email} reported {complaint.category} in {complaint.building} ({complaint.location_detail})",
        notification_type="complaint",
        reference_id=complaint.complaint_code,
        is_read=False,
        created_at=now,
    )
    db.add(notification)

    db.commit()
    db.refresh(complaint)

    return _format_complaint(complaint, db)


@router.get(
    "/mine",
    summary="List complaints for current student (used by frontend)",
)
def get_my_complaints(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Complaint).filter(
        models.Complaint.student_id == current_user.id
    ).order_by(models.Complaint.created_at.desc())
    items = query.offset(offset).limit(limit).all()
    formatted = [_format_complaint(c, db) for c in items]
    return {
        "items": formatted,
        "count": len(formatted),
        "total_count": query.count(),
        "data_source": "simulated",
    }


# ===========================================================================
# Admin Notifications (SPEC §10) — MUST be defined BEFORE /{complaint_id}
# ===========================================================================
@router.get(
    "/admin/notifications",
    response_model=AdminNotificationListResponse,
    summary="Get admin notification records for new complaints and events (Admin only)",
)
@router.get(
    "/notifications/admin",
    response_model=AdminNotificationListResponse,
    summary="Get admin notification records for new complaints and events (Admin only) - Alias",
)
def get_admin_notifications(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Retrieve internal admin notification logs for student complaints."""
    notifs = (
        db.query(models.AdminNotification)
        .order_by(models.AdminNotification.created_at.desc())
        .limit(limit)
        .all()
    )
    items = [
        AdminNotificationItem(
            id=n.id,
            title=n.title,
            message=n.message,
            notification_type=n.notification_type,
            reference_id=n.reference_id,
            is_read=n.is_read,
            created_at=n.created_at.isoformat() if n.created_at else "",
            data_source="simulated",
        )
        for n in notifs
    ]
    unread = sum(1 for n in items if not n.is_read)

    return AdminNotificationListResponse(
        notifications=items,
        unread_count=unread,
        count=len(items),
        data_source="simulated",
    )


@router.patch(
    "/admin/notifications/{notification_id}/read",
    summary="Mark one admin notification as read (Admin only)",
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    notif = db.query(models.AdminNotification).filter(models.AdminNotification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"id": notif.id, "is_read": True, "data_source": "simulated"}


@router.post(
    "/admin/notifications/read-all",
    summary="Mark every admin notification as read (Admin only)",
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    updated = (
        db.query(models.AdminNotification)
        .filter(models.AdminNotification.is_read == False)  # noqa: E712
        .update({models.AdminNotification.is_read: True})
    )
    db.commit()
    return {"updated": updated, "data_source": "simulated"}


@router.get(
    "/assignees",
    summary="List staff accounts a complaint can be assigned to (Admin only)",
)
def list_assignees(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    staff = (
        db.query(models.User)
        .filter(models.User.role == "admin", models.User.is_active == True)  # noqa: E712
        .order_by(models.User.id.asc())
        .all()
    )
    return {
        "assignees": [
            {"id": u.id, "email": u.email, "name": u.full_name or u.username} for u in staff
        ],
        "data_source": "simulated",
    }


@router.get(
    "",
    response_model=ComplaintListResponse,
    summary="List complaints (Students see only own; Admins see all with filters)",
)
def get_complaints(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    building_filter: Optional[str] = Query(None, alias="building", description="Filter by building"),
    category_filter: Optional[str] = Query(None, alias="category", description="Filter by category"),
    limit: int = Query(100, ge=1, le=500, description="Max complaints to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieve complaints list:
    - Students see strictly only their own submitted complaints.
    - Administrators see campus-wide complaints with optional status, building, and category filters.
    - Includes overdue calculation and frequently affected location statistics.
    """
    query = db.query(models.Complaint).order_by(models.Complaint.created_at.desc())

    if current_user.role == "student":
        # Role restriction: students only see their own complaints
        query = query.filter(models.Complaint.student_id == current_user.id)
    else:
        # Admin filters
        if status_filter:
            query = query.filter(models.Complaint.status == status_filter.lower())
        if building_filter:
            query = query.filter(models.Complaint.building == building_filter)
        if category_filter:
            query = query.filter(models.Complaint.category == category_filter.lower())

    total_matching = query.count()
    complaints_list = query.offset(offset).limit(limit).all()
    formatted = [_format_complaint(c, db) for c in complaints_list]
    overdue_count = sum(1 for c in formatted if c.is_overdue)

    # Compute frequently affected locations across all complaints
    all_complaints = db.query(models.Complaint).all()
    loc_counts = {}
    for c in all_complaints:
        key = (c.building, c.location_detail)
        loc_counts[key] = loc_counts.get(key, 0) + 1

    frequently_affected = [
        FrequentlyAffectedLocation(building=b, location_detail=ld, count=cnt)
        for (b, ld), cnt in sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    return ComplaintListResponse(
        complaints=formatted,
        count=len(formatted),
        overdue_count=overdue_count,
        frequently_affected_locations=frequently_affected,
        limit=limit,
        offset=offset,
        total_count=total_matching,
        data_source="simulated",
    )


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Get single complaint by ID",
)
def get_complaint_by_id(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Fetch details of a single complaint.
    Enforces privacy: a student cannot read another student's complaint (403 Forbidden).
    """
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id {complaint_id} not found",
        )

    # Privacy check: student cannot view another student's complaint
    if current_user.role == "student" and complaint.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: student cannot view another student's complaint",
        )

    return _format_complaint(complaint, db)


@router.patch(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Update complaint lifecycle, assign, or add notes (Admin only)",
)
def update_complaint(
    complaint_id: int,
    payload: ComplaintPatch,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Admin-only complaint triage:
    - Status lifecycle transitions: submitted -> acknowledged -> assigned -> in_progress -> resolved -> reopened.
    - Assignment to maintenance staff/admin.
    - Logging every change to complaint_history.
    """
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id {complaint_id} not found",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_status = complaint.status
    audit_notes = []

    # 1. Status update with lifecycle transition validation
    if payload.status is not None:
        new_status = payload.status.strip().lower().replace(" ", "_")
        all_known = set(VALID_STATUS_LIFECYCLE.keys())
        if new_status not in all_known:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{payload.status}'. Must be one of: {sorted(all_known)}",
            )

        if new_status != old_status:
            allowed = VALID_STATUS_LIFECYCLE.get(old_status, set())
            if new_status not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid lifecycle transition from '{old_status}' to '{new_status}'. Allowed: {sorted(allowed)}",
                )
            complaint.status = new_status
            audit_notes.append(f"Status changed from '{old_status}' to '{new_status}'")

    # 2. Assignment update
    if payload.assigned_to is not None:
        staff = db.query(models.User).filter(models.User.id == payload.assigned_to).first()
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assigned user id {payload.assigned_to} not found",
            )
        if staff.role != "admin" or not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Complaints can only be assigned to active admin / maintenance staff accounts.",
            )
        complaint.assigned_to = payload.assigned_to
        audit_notes.append(f"Assigned to {staff.email}")

        # Automatically progress submitted/acknowledged complaints to 'assigned' if status was not explicitly set
        if complaint.status in ("submitted", "acknowledged") and payload.status is None:
            old_status = complaint.status
            complaint.status = "assigned"
            audit_notes.append("Status automatically advanced to 'assigned'")

    # 3. Resolution notes
    if payload.resolution_notes is not None:
        complaint.resolution_notes = payload.resolution_notes
        audit_notes.append("Updated resolution notes")

    complaint.updated_at = now

    # 4. Log in complaint_history
    summary_note = "; ".join(audit_notes) if audit_notes else (payload.notes or "Updated complaint details")
    history_entry = models.ComplaintHistory(
        complaint_id=complaint.id,
        changed_by=admin_user.id,
        old_status=old_status,
        new_status=complaint.status,
        note=payload.notes or summary_note,
        changed_at=now,
    )
    db.add(history_entry)

    db.commit()
    db.refresh(complaint)

    return _format_complaint(complaint, db)


@router.post(
    "/{complaint_id}/reopen",
    response_model=ComplaintResponse,
    summary="Reopen a resolved complaint (owner student or admin)",
)
def reopen_complaint(
    complaint_id: int,
    payload: Optional[ComplaintReopen] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """The student who filed a complaint (or an admin) can reopen it if the problem came back."""
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Complaint with id {complaint_id} not found")
    if current_user.role != "admin" and complaint.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: you can only reopen your own complaints")
    if complaint.status != "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only resolved complaints can be reopened (current status: '{complaint.status}').",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_status = complaint.status
    complaint.status = "reopened"
    complaint.updated_at = now
    reason = (payload.reason.strip() if payload and payload.reason else "") or "Issue reported again by the reporter"
    db.add(
        models.ComplaintHistory(
            complaint_id=complaint.id,
            changed_by=current_user.id,
            old_status=old_status,
            new_status="reopened",
            note=reason[:500],
            changed_at=now,
        )
    )
    db.add(
        models.AdminNotification(
            title=f"Complaint reopened: {complaint.complaint_code}",
            message=f"{current_user.email} reopened {complaint.complaint_code} ({complaint.building} - {complaint.location_detail})",
            notification_type="complaint",
            reference_id=complaint.complaint_code,
            is_read=False,
            created_at=now,
        )
    )
    db.commit()
    db.refresh(complaint)
    return _format_complaint(complaint, db)


# NOTE: static routes (/mine, /assignees, /admin/notifications...) are defined before
# /{complaint_id} so FastAPI never tries to parse them as an integer complaint ID.
