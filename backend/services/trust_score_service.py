"""Trust score calculation service."""
from backend.utils import db


async def calculate_trust_score(department_id: int) -> float:
    """Calculate trust score for a department based on resolution rate and feedback."""
    stats = await db.fetch_one(
        """
        SELECT 
            COUNT(*) as total_assigned,
            COUNT(CASE WHEN g.status = 'RESOLVED' THEN 1 END) as total_resolved
        FROM grievance_assignments ga
        JOIN grievances g ON ga.grievance_id = g.grievance_id
        WHERE ga.department_id = $1
        """,
        department_id
    )
    
    if not stats or stats['total_assigned'] == 0:
        return 0.0
    
    resolution_rate = stats['total_resolved'] / stats['total_assigned']
    
    feedback_stats = await db.fetch_one(
        """
        SELECT AVG(f.rating) as avg_rating
        FROM feedback f
        JOIN grievance_assignments ga ON f.grievance_id = ga.grievance_id
        WHERE ga.department_id = $1
        """,
        department_id
    )
    
    avg_rating = feedback_stats['avg_rating'] if feedback_stats and feedback_stats['avg_rating'] else 3.0
    
    trust_score = (resolution_rate * 0.4) + ((avg_rating / 5) * 0.6)
    trust_score = round(trust_score, 2)
    
    await db.execute(
        "UPDATE departments SET trust_score = $1 WHERE department_id = $2",
        trust_score, department_id
    )
    
    return trust_score


async def update_all_trust_scores():
    """Update trust scores for all departments."""
    departments = await db.fetch_all("SELECT department_id FROM departments")
    
    for dept in departments:
        await calculate_trust_score(dept['department_id'])


async def get_department_performance() -> list:
    """Get performance metrics for all departments."""
    results = await db.fetch_all(
        """
        SELECT 
            d.department_id,
            d.department_name,
            d.trust_score,
            COUNT(DISTINCT ga.grievance_id) as total_assigned,
            COUNT(DISTINCT CASE WHEN g.status = 'RESOLVED' THEN ga.grievance_id END) as total_resolved,
            COALESCE(AVG(f.rating), 0) as avg_rating
        FROM departments d
        LEFT JOIN grievance_assignments ga ON d.department_id = ga.department_id
        LEFT JOIN grievances g ON ga.grievance_id = g.grievance_id
        LEFT JOIN feedback f ON ga.grievance_id = f.grievance_id
        GROUP BY d.department_id, d.department_name, d.trust_score
        ORDER BY d.trust_score DESC
        """
    )
    
    return [
        {
            **dict(r),
            'resolution_rate': round(r['total_resolved'] / r['total_assigned'] * 100, 1) if r['total_assigned'] > 0 else 0
        }
        for r in results
    ]
