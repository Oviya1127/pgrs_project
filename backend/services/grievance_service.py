"""Grievance service for CRUD operations."""
from typing import Optional, List
from backend.utils import db, generate_grievance_id, GrievanceStatus, Messages
from backend.models import GrievanceCreate, GrievanceResponse, GrievanceDetail, GrievanceFilter
from .priority_service import calculate_priority
from .sentiment_service import analyze_and_store_sentiment


async def create_grievance(user_id: int, grievance_data: GrievanceCreate) -> dict:
    """Create a new grievance."""
    grievance_id = generate_grievance_id()
    
    while True:
        existing = await db.fetch_one(
            "SELECT grievance_id FROM grievances WHERE grievance_id = $1",
            grievance_id
        )
        if not existing:
            break
        grievance_id = generate_grievance_id()
    
    result = await db.fetch_one(
        """
        INSERT INTO grievances (grievance_id, user_id, category_id, location_id, complaint_text, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING grievance_id, user_id, category_id, location_id, complaint_text, status, created_at
        """,
        grievance_id,
        user_id,
        grievance_data.category_id,
        grievance_data.location_id,
        grievance_data.complaint_text,
        GrievanceStatus.SUBMITTED
    )

    await analyze_and_store_sentiment(grievance_id, grievance_data.complaint_text)
    await calculate_priority(grievance_id)
    
    return {
        "success": True,
        "message": Messages.GRIEVANCE_SUBMITTED,
        "data": {
            "grievance_id": result['grievance_id'],
            "status": result['status'],
            "created_at": result['created_at'].isoformat()
        }
    }


async def get_user_grievances(user_id: int, page: int = 1, per_page: int = 10) -> dict:
    """Get all grievances for a user."""
    offset = (page - 1) * per_page
    
    grievances = await db.fetch_all(
        """
        SELECT g.grievance_id, g.user_id, g.category_id, c.category_name,
               g.location_id, CONCAT(l.state, ', ', l.district) as location_details,
               g.complaint_text, g.status, g.created_at,
               p.priority_level, s.compound_score,
               (SELECT COUNT(*) FROM peer_validations pv WHERE pv.grievance_id = g.grievance_id) as peer_count
        FROM grievances g
        LEFT JOIN categories c ON g.category_id = c.category_id
        LEFT JOIN locations l ON g.location_id = l.location_id
        LEFT JOIN priorities p ON g.grievance_id = p.grievance_id
        LEFT JOIN sentiment_analysis s ON g.grievance_id = s.grievance_id
        WHERE g.user_id = $1
        ORDER BY g.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id, per_page, offset
    )
    
    total = await db.fetch_one(
        "SELECT COUNT(*) as count FROM grievances WHERE user_id = $1",
        user_id
    )
    
    return {
        "success": True,
        "data": {
            "items": [dict(g) for g in grievances],
            "total": total['count'] if total else 0,
            "page": page,
            "per_page": per_page
        }
    }


async def get_grievance_by_id(grievance_id: str, user_id: Optional[int] = None) -> dict:
    """Get a specific grievance by ID."""
    query = """
        SELECT g.grievance_id, g.user_id, u.full_name as user_name,
               g.category_id, c.category_name,
               g.location_id, CONCAT(l.state, ', ', l.district, COALESCE(', ' || l.zone_name, ''), COALESCE(', ' || l.ward, '')) as location_details,
               g.complaint_text, g.status, g.created_at,
               p.priority_level, s.compound_score,
               (SELECT COUNT(*) FROM peer_validations pv WHERE pv.grievance_id = g.grievance_id) as peer_count
        FROM grievances g
        LEFT JOIN users u ON g.user_id = u.user_id
        LEFT JOIN categories c ON g.category_id = c.category_id
        LEFT JOIN locations l ON g.location_id = l.location_id
        LEFT JOIN priorities p ON g.grievance_id = p.grievance_id
        LEFT JOIN sentiment_analysis s ON g.grievance_id = s.grievance_id
        WHERE g.grievance_id = $1
    """
    
    grievance = await db.fetch_one(query, grievance_id)
    
    if not grievance:
        return {"success": False, "message": Messages.GRIEVANCE_NOT_FOUND}
    
    assignment = await db.fetch_one(
        """
        SELECT ga.assignment_id, ga.department_id, d.department_name,
               ga.admin_id, u.full_name as admin_name, ga.assigned_at
        FROM grievance_assignments ga
        LEFT JOIN departments d ON ga.department_id = d.department_id
        LEFT JOIN admins a ON ga.admin_id = a.admin_id
        LEFT JOIN users u ON a.user_id = u.user_id
        WHERE ga.grievance_id = $1
        ORDER BY ga.assigned_at DESC LIMIT 1
        """,
        grievance_id
    )
    
    feedback = await db.fetch_one(
        """
        SELECT feedback_id, rating, comments, submitted_at
        FROM feedback WHERE grievance_id = $1
        """,
        grievance_id
    )
    
    duplicates = await db.fetch_all(
        """
        SELECT child_grievance_id FROM duplicate_grievances
        WHERE parent_grievance_id = $1
        UNION
        SELECT parent_grievance_id FROM duplicate_grievances
        WHERE child_grievance_id = $1
        """,
        grievance_id
    )
    
    result = dict(grievance)
    result['assignment'] = dict(assignment) if assignment else None
    result['feedback'] = dict(feedback) if feedback else None
    result['duplicates'] = [d['child_grievance_id'] if 'child_grievance_id' in d else d['parent_grievance_id'] for d in duplicates]
    
    return {"success": True, "data": result}


async def get_all_grievances(filters: GrievanceFilter) -> dict:
    """Get all grievances with filters (for admin)."""
    conditions = ["1=1"]
    values = []
    param_count = 1
    
    if filters.status:
        conditions.append(f"g.status = ${param_count}")
        values.append(filters.status)
        param_count += 1
    
    if filters.category_id:
        conditions.append(f"g.category_id = ${param_count}")
        values.append(filters.category_id)
        param_count += 1
    
    if filters.priority_level:
        conditions.append(f"p.priority_level = ${param_count}")
        values.append(filters.priority_level)
        param_count += 1
    
    if filters.location_id:
        conditions.append(f"g.location_id = ${param_count}")
        values.append(filters.location_id)
        param_count += 1

    if filters.search:
        conditions.append(f"(g.grievance_id ILIKE ${param_count} OR u.full_name ILIKE ${param_count})")
        values.append(f"%{filters.search}%")
        param_count += 1
    
    offset = (filters.page - 1) * filters.per_page
    values.extend([filters.per_page, offset])
    
    query = f"""
        SELECT g.grievance_id, g.user_id, u.full_name as user_name,
               g.category_id, c.category_name,
               g.location_id, CONCAT(l.state, ', ', l.district) as location_details,
               g.complaint_text, g.status, g.created_at,
               p.priority_level, s.compound_score,
               (SELECT COUNT(*) FROM peer_validations pv WHERE pv.grievance_id = g.grievance_id) as peer_count
        FROM grievances g
        LEFT JOIN users u ON g.user_id = u.user_id
        LEFT JOIN categories c ON g.category_id = c.category_id
        LEFT JOIN locations l ON g.location_id = l.location_id
        LEFT JOIN priorities p ON g.grievance_id = p.grievance_id
        LEFT JOIN sentiment_analysis s ON g.grievance_id = s.grievance_id
        WHERE {' AND '.join(conditions)}
        ORDER BY 
            CASE p.priority_level 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                WHEN 'LOW' THEN 4 
                ELSE 5 
            END,
            g.created_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    
    grievances = await db.fetch_all(query, *values)
    
    count_query = f"""
        SELECT COUNT(*) as count
        FROM grievances g
        LEFT JOIN priorities p ON g.grievance_id = p.grievance_id
        LEFT JOIN users u ON g.user_id = u.user_id
        WHERE {' AND '.join(conditions)}
    """
    total = await db.fetch_one(count_query, *values[:-2])
    
    return {
        "success": True,
        "data": {
            "items": [dict(g) for g in grievances],
            "total": total['count'] if total else 0,
            "page": filters.page,
            "per_page": filters.per_page
        }
    }


async def update_grievance_status(grievance_id: str, status: str) -> dict:
    """Update grievance status."""
    result = await db.fetch_one(
        """
        UPDATE grievances SET status = $1
        WHERE grievance_id = $2
        RETURNING grievance_id, status
        """,
        status, grievance_id
    )
    
    if not result:
        return {"success": False, "message": Messages.GRIEVANCE_NOT_FOUND}
    
    return {
        "success": True,
        "message": Messages.GRIEVANCE_UPDATED,
        "data": dict(result)
    }


async def add_peer_validation(grievance_id: str, user_id: int) -> dict:
    """Add a peer validation to a grievance."""
    grievance = await db.fetch_one(
        "SELECT user_id FROM grievances WHERE grievance_id = $1",
        grievance_id
    )
    
    if not grievance:
        return {"success": False, "message": Messages.GRIEVANCE_NOT_FOUND}
    
    if grievance['user_id'] == user_id:
        return {"success": False, "message": Messages.OWN_GRIEVANCE}
    
    existing = await db.fetch_one(
        "SELECT validation_id FROM peer_validations WHERE grievance_id = $1 AND user_id = $2",
        grievance_id, user_id
    )
    
    if existing:
        return {"success": False, "message": Messages.ALREADY_VALIDATED}
    
    await db.execute(
        "INSERT INTO peer_validations (grievance_id, user_id) VALUES ($1, $2)",
        grievance_id, user_id
    )
    
    count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM peer_validations WHERE grievance_id = $1",
        grievance_id
    )

    await calculate_priority(grievance_id)
    
    return {
        "success": True,
        "message": Messages.VALIDATION_SUCCESS,
        "data": {
            "grievance_id": grievance_id,
            "total_validations": count['count'] if count else 1
        }
    }


async def get_categories() -> List[dict]:
    """Get all categories."""
    categories = await db.fetch_all("SELECT category_id, category_name FROM categories ORDER BY category_name")
    return [dict(c) for c in categories]


async def get_locations() -> List[dict]:
    """Get all locations."""
    locations = await db.fetch_all(
        "SELECT location_id, state, district, zone_name, ward, place_name FROM locations ORDER BY state, district"
    )
    return [dict(l) for l in locations]


async def find_similar_grievances(category_id: int, location_id: int, complaint_text: str) -> List[dict]:
    """Find similar grievances for duplicate detection."""
    keywords = complaint_text.lower().split()[:5]  # First 5 words
    
    grievances = await db.fetch_all(
        """
        SELECT g.grievance_id, g.complaint_text, g.status, g.created_at,
               (SELECT COUNT(*) FROM peer_validations pv WHERE pv.grievance_id = g.grievance_id) as peer_count
        FROM grievances g
        WHERE g.category_id = $1 
        AND g.location_id = $2
        AND g.status != 'RESOLVED'
        ORDER BY g.created_at DESC
        LIMIT 5
        """,
        category_id, location_id
    )
    
    return [dict(g) for g in grievances]
