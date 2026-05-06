"""Admin routes."""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from backend.models import GrievanceFilter, GrievanceUpdate, GrievanceAssignment, BaseResponse
from backend.services import (
    get_all_grievances, get_grievance_by_id, update_grievance_status,
    assign_grievance, get_departments, get_admins, notify_status_change
)
from backend.utils import db
from backend.middleware import get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/grievances")
async def list_all_grievances(
    current_user = Depends(get_current_user),
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    priority_level: Optional[str] = None,
    location_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    """Get all grievances with filters (admin only)."""
    await require_admin(current_user)
    
    filters = GrievanceFilter(
        status=status,
        category_id=category_id,
        priority_level=priority_level,
        location_id=location_id,
        search=search,
        page=page,
        per_page=per_page
    )
    result = await get_all_grievances(filters)
    return result


@router.get("/grievances/{grievance_id}")
async def get_grievance(grievance_id: str, current_user = Depends(get_current_user)):
    """Get grievance details (admin)."""
    await require_admin(current_user)
    
    result = await get_grievance_by_id(grievance_id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    return result


@router.put("/grievances/{grievance_id}/status")
async def update_status(
    grievance_id: str,
    update: GrievanceUpdate,
    current_user = Depends(get_current_user)
):
    """Update grievance status (admin only)."""
    await require_admin(current_user)
    
    result = await update_grievance_status(grievance_id, update.status)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    await notify_status_change(grievance_id, update.status)
    
    return result


@router.post("/grievances/{grievance_id}/assign")
async def assign_to_department(
    grievance_id: str,
    assignment: GrievanceAssignment,
    current_user = Depends(get_current_user)
):
    """Assign grievance to department (admin only)."""
    await require_admin(current_user)
    
    result = await assign_grievance(
        grievance_id,
        assignment.department_id,
        assignment.admin_id
    )
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.get("/departments")
async def list_departments(current_user = Depends(get_current_user)):
    """Get all departments."""
    await require_admin(current_user)
    
    departments = await get_departments()
    return {"success": True, "data": departments}


@router.get("/admins")
async def list_admins(current_user = Depends(get_current_user)):
    """Get all admins."""
    await require_admin(current_user)
    
    admins = await get_admins()
    return {"success": True, "data": admins}


@router.get("/users/count")
async def get_users_count(current_user = Depends(get_current_user)):
    """Get total number of registered users (admin only)."""
    await require_admin(current_user)

    row = await db.fetch_one("SELECT COUNT(*) as total FROM users")
    total = int(row['total']) if row and row.get('total') is not None else 0
    return {"success": True, "data": {"total_users": total}}


@router.get("/users")
async def list_users_with_counts(current_user = Depends(get_current_user), page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200)):
    """Return users with their grievance counts and statuses (admin only)."""
    await require_admin(current_user)

    offset = (page - 1) * per_page
    users = await db.fetch_all(
        """
        SELECT u.user_id, u.full_name, u.email, u.phone, u.role,
               COALESCE(g.total, 0) as total_grievances,
               COALESCE(g.submitted, 0) as submitted,
               COALESCE(g.in_progress, 0) as in_progress,
               COALESCE(g.resolved, 0) as resolved
        FROM users u
        LEFT JOIN (
            SELECT user_id,
                   COUNT(*) as total,
                   COUNT(CASE WHEN status = 'SUBMITTED' THEN 1 END) as submitted,
                   COUNT(CASE WHEN status = 'IN_PROGRESS' THEN 1 END) as in_progress,
                   COUNT(CASE WHEN status = 'RESOLVED' THEN 1 END) as resolved
            FROM grievances
            GROUP BY user_id
        ) g ON u.user_id = g.user_id
        ORDER BY u.created_at DESC NULLS LAST
        LIMIT $1 OFFSET $2
        """,
        per_page, offset
    )

    return {"success": True, "data": [dict(u) for u in users]}


@router.get("/feedback")
async def list_all_feedback(
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """List all feedback for admin (accountability, ratings)."""
    await require_admin(current_user)
    offset = (page - 1) * per_page
    rows = await db.fetch_all(
        """
        SELECT f.feedback_id, f.grievance_id, f.user_id, u.full_name as user_name,
               f.rating, f.comments, f.submitted_at
        FROM feedback f
        JOIN users u ON f.user_id = u.user_id
        ORDER BY f.submitted_at DESC
        LIMIT $1 OFFSET $2
        """,
        per_page,
        offset,
    )
    total = await db.fetch_one("SELECT COUNT(*) as c FROM feedback")
    return {
        "success": True,
        "data": {"items": [dict(r) for r in rows], "total": total["c"] if total else 0},
    }


@router.get("/alerts")
async def get_alerts(current_user=Depends(get_current_user)):
    """Critical unassigned count, pending count for notifications/escalations."""
    await require_admin(current_user)
    critical_unassigned = await db.fetch_one(
        """
        SELECT COUNT(*) as c FROM grievances g
        JOIN priorities p ON p.grievance_id = g.grievance_id
        WHERE g.status = 'SUBMITTED' AND p.priority_level = 'CRITICAL'
        AND NOT EXISTS (SELECT 1 FROM grievance_assignments ga WHERE ga.grievance_id = g.grievance_id)
        """
    )
    pending = await db.fetch_one(
        "SELECT COUNT(*) as c FROM grievances WHERE status = 'SUBMITTED'"
    )
    return {
        "success": True,
        "data": {
            "critical_unassigned": critical_unassigned["c"] if critical_unassigned else 0,
            "pending_count": pending["c"] if pending else 0,
        },
    }
