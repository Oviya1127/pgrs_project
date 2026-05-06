"""Analytics routes."""
from fastapi import APIRouter, Depends
from backend.middleware import get_current_user, require_admin
from backend.utils import db
from backend.services import get_priority_distribution, get_department_performance

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_overview(current_user = Depends(get_current_user)):
    """Get dashboard overview statistics."""
    await require_admin(current_user)
    
    status_stats = await db.fetch_all(
        """
        SELECT status, COUNT(*) as count
        FROM grievances
        GROUP BY status
        """
    )
    
    monthly_stats = await db.fetch_one(
        """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'RESOLVED' THEN 1 END) as resolved
        FROM grievances
        WHERE created_at >= date_trunc('month', CURRENT_DATE)
        """
    )
    
    priority_dist = await get_priority_distribution()
    
    avg_resolution = await db.fetch_one(
        """
        SELECT AVG(EXTRACT(EPOCH FROM (
            COALESCE(
                (SELECT MAX(assigned_at) FROM grievance_assignments WHERE grievance_id = g.grievance_id),
                g.created_at
            ) - g.created_at
        )) / 3600) as avg_hours
        FROM grievances g
        WHERE g.status = 'RESOLVED'
        """
    )
    
    return {
        "success": True,
        "data": {
            "status_distribution": {row['status']: row['count'] for row in status_stats},
            "monthly": dict(monthly_stats) if monthly_stats else {"total": 0, "resolved": 0},
            "priority_distribution": priority_dist,
            "avg_resolution_hours": round(avg_resolution['avg_hours'], 1) if avg_resolution and avg_resolution['avg_hours'] else 0
        }
    }


@router.get("/categories")
async def get_category_analytics(current_user = Depends(get_current_user)):
    """Get category-wise grievance distribution."""
    await require_admin(current_user)
    
    categories = await db.fetch_all(
        """
        SELECT c.category_id, c.category_name, 
               COUNT(g.grievance_id) as total_grievances,
               COUNT(CASE WHEN g.status = 'RESOLVED' THEN 1 END) as resolved,
               COUNT(CASE WHEN g.status = 'IN_PROGRESS' THEN 1 END) as in_progress,
               COUNT(CASE WHEN g.status = 'SUBMITTED' THEN 1 END) as pending
        FROM categories c
        LEFT JOIN grievances g ON c.category_id = g.category_id
        GROUP BY c.category_id, c.category_name
        ORDER BY total_grievances DESC
        """
    )
    
    return {"success": True, "data": [dict(c) for c in categories]}


@router.get("/locations")
async def get_location_analytics(current_user = Depends(get_current_user)):
    """Get location-wise grievance distribution."""
    await require_admin(current_user)
    
    locations = await db.fetch_all(
        """
        SELECT l.district, l.state,
               COUNT(g.grievance_id) as total_grievances,
               COUNT(CASE WHEN g.status = 'RESOLVED' THEN 1 END) as resolved
        FROM locations l
        LEFT JOIN grievances g ON l.location_id = g.location_id
        GROUP BY l.district, l.state
        ORDER BY total_grievances DESC
        LIMIT 20
        """
    )
    
    return {"success": True, "data": [dict(l) for l in locations]}


@router.get("/departments")
async def get_department_analytics(current_user = Depends(get_current_user)):
    """Get department performance metrics."""
    await require_admin(current_user)
    
    performance = await get_department_performance()
    return {"success": True, "data": performance}


@router.get("/trends")
async def get_trends(current_user = Depends(get_current_user)):
    """Get grievance trends over time."""
    await require_admin(current_user)
    
    trends = await db.fetch_all(
        """
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as submitted,
            COUNT(CASE WHEN status = 'RESOLVED' THEN 1 END) as resolved
        FROM grievances
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date
        """
    )
    
    return {"success": True, "data": [dict(t) for t in trends]}
