"""Priority calculation service."""
from backend.utils import db, PriorityLevel, SentimentThreshold, PeerThreshold


async def calculate_priority(grievance_id: str) -> str:
    """Calculate priority level for a grievance based on sentiment and peer count."""
    sentiment = await db.fetch_one(
        "SELECT compound_score FROM sentiment_analysis WHERE grievance_id = $1",
        grievance_id
    )
    compound_score = sentiment['compound_score'] if sentiment else 0.0
    
    peer_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM peer_validations WHERE grievance_id = $1",
        grievance_id
    )
    peer_count = peer_count['count'] if peer_count else 0
    
    priority_level = _determine_priority(compound_score, peer_count)
    
    existing = await db.fetch_one(
        "SELECT priority_id FROM priorities WHERE grievance_id = $1",
        grievance_id
    )
    
    if existing:
        await db.execute(
            "UPDATE priorities SET priority_level = $1, calculated_at = CURRENT_TIMESTAMP WHERE grievance_id = $2",
            priority_level, grievance_id
        )
    else:
        await db.execute(
            "INSERT INTO priorities (grievance_id, priority_level) VALUES ($1, $2)",
            grievance_id, priority_level
        )
    
    return priority_level


def _determine_priority(compound_score: float, peer_count: int) -> str:
    """Determine priority level based on sentiment score and peer count."""
    if peer_count >= PeerThreshold.CRITICAL:
        return PriorityLevel.CRITICAL
    elif peer_count >= PeerThreshold.HIGH:
        peer_priority = PriorityLevel.HIGH
    elif peer_count >= PeerThreshold.MEDIUM:
        peer_priority = PriorityLevel.MEDIUM
    else:
        peer_priority = PriorityLevel.LOW
    
    if compound_score <= SentimentThreshold.CRITICAL:
        sentiment_priority = PriorityLevel.CRITICAL
    elif compound_score <= SentimentThreshold.HIGH:
        sentiment_priority = PriorityLevel.HIGH
    elif compound_score <= SentimentThreshold.MEDIUM:
        sentiment_priority = PriorityLevel.MEDIUM
    else:
        sentiment_priority = PriorityLevel.LOW
    
    priority_order = {
        PriorityLevel.LOW: 1,
        PriorityLevel.MEDIUM: 2,
        PriorityLevel.HIGH: 3,
        PriorityLevel.CRITICAL: 4
    }
    
    if priority_order[peer_priority] >= priority_order[sentiment_priority]:
        return peer_priority
    return sentiment_priority


async def get_priority_distribution() -> dict:
    """Get distribution of priorities for analytics."""
    result = await db.fetch_all(
        """
        SELECT priority_level, COUNT(*) as count
        FROM priorities
        GROUP BY priority_level
        """
    )
    
    distribution = {
        PriorityLevel.LOW: 0,
        PriorityLevel.MEDIUM: 0,
        PriorityLevel.HIGH: 0,
        PriorityLevel.CRITICAL: 0
    }
    
    for row in result:
        distribution[row['priority_level']] = row['count']
    
    return distribution
