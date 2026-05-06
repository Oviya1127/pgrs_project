"""Grievance assignment service."""
from typing import Optional
from backend.utils import db, Messages


async def assign_grievance(grievance_id: str, department_id: int, admin_id: Optional[int] = None) -> dict:
    """Assign a grievance to a department and optionally an admin."""
    grievance = await db.fetch_one(
        "SELECT grievance_id FROM grievances WHERE grievance_id = $1",
        grievance_id
    )
    if not grievance:
        return {"success": False, "message": Messages.GRIEVANCE_NOT_FOUND}
    
    department = await db.fetch_one(
        "SELECT department_id, department_name FROM departments WHERE department_id = $1",
        department_id
    )
    if not department:
        return {"success": False, "message": "Department not found"}
    
    existing = await db.fetch_one(
        "SELECT assignment_id FROM grievance_assignments WHERE grievance_id = $1",
        grievance_id
    )
    
    if existing:
        result = await db.fetch_one(
            """
            UPDATE grievance_assignments 
            SET department_id = $1, admin_id = $2, assigned_at = CURRENT_TIMESTAMP
            WHERE grievance_id = $3
            RETURNING assignment_id, grievance_id, department_id, admin_id, assigned_at
            """,
            department_id, admin_id, grievance_id
        )
    else:
        result = await db.fetch_one(
            """
            INSERT INTO grievance_assignments (grievance_id, department_id, admin_id)
            VALUES ($1, $2, $3)
            RETURNING assignment_id, grievance_id, department_id, admin_id, assigned_at
            """,
            grievance_id, department_id, admin_id
        )
    
    await db.execute(
        "UPDATE grievances SET status = 'IN_PROGRESS' WHERE grievance_id = $1",
        grievance_id
    )
    
    return {
        "success": True,
        "message": "Grievance assigned successfully",
        "data": {
            **dict(result),
            "department_name": department['department_name']
        }
    }


async def get_departments() -> list:
    """Get all departments."""
    departments = await db.fetch_all(
        "SELECT department_id, department_name, trust_score FROM departments ORDER BY department_name"
    )
    return [dict(d) for d in departments]


async def get_department_assignments(department_id: int) -> list:
    """Get all assignments for a department."""
    assignments = await db.fetch_all(
        """
        SELECT ga.assignment_id, ga.grievance_id, g.complaint_text, g.status,
               ga.admin_id, u.full_name as admin_name, ga.assigned_at
        FROM grievance_assignments ga
        JOIN grievances g ON ga.grievance_id = g.grievance_id
        LEFT JOIN admins a ON ga.admin_id = a.admin_id
        LEFT JOIN users u ON a.user_id = u.user_id
        WHERE ga.department_id = $1
        ORDER BY ga.assigned_at DESC
        """,
        department_id
    )
    return [dict(a) for a in assignments]


async def get_admins() -> list:
    """Get all admins."""
    admins = await db.fetch_all(
        """
        SELECT a.admin_id, a.user_id, u.full_name, u.email
        FROM admins a
        JOIN users u ON a.user_id = u.user_id
        ORDER BY u.full_name
        """
    )
    return [dict(a) for a in admins]
