"""Notification service."""
from typing import List
from backend.utils import db


async def create_notification(user_id: int, message: str) -> dict:
    """Create a notification for a user."""
    result = await db.fetch_one(
        """
        INSERT INTO notifications (user_id, message)
        VALUES ($1, $2)
        RETURNING notification_id, user_id, message, is_read, created_at
        """,
        user_id, message
    )
    return dict(result)


async def get_user_notifications(user_id: int, unread_only: bool = False) -> List[dict]:
    """Get notifications for a user."""
    if unread_only:
        notifications = await db.fetch_all(
            """
            SELECT notification_id, user_id, message, is_read, created_at
            FROM notifications
            WHERE user_id = $1 AND is_read = FALSE
            ORDER BY created_at DESC
            """,
            user_id
        )
    else:
        notifications = await db.fetch_all(
            """
            SELECT notification_id, user_id, message, is_read, created_at
            FROM notifications
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 50
            """,
            user_id
        )
    return [dict(n) for n in notifications]


async def mark_as_read(notification_id: int, user_id: int) -> dict:
    """Mark a notification as read."""
    result = await db.execute(
        """
        UPDATE notifications SET is_read = TRUE
        WHERE notification_id = $1 AND user_id = $2
        """,
        notification_id, user_id
    )
    return {"success": True, "message": "Notification marked as read"}


async def mark_all_as_read(user_id: int) -> dict:
    """Mark all notifications as read for a user."""
    await db.execute(
        "UPDATE notifications SET is_read = TRUE WHERE user_id = $1",
        user_id
    )
    return {"success": True, "message": "All notifications marked as read"}


async def get_unread_count(user_id: int) -> int:
    """Get count of unread notifications."""
    result = await db.fetch_one(
        "SELECT COUNT(*) as count FROM notifications WHERE user_id = $1 AND is_read = FALSE",
        user_id
    )
    return result['count'] if result else 0


async def notify_status_change(grievance_id: str, new_status: str):
    """Send notification when grievance status changes."""
    grievance = await db.fetch_one(
        "SELECT user_id FROM grievances WHERE grievance_id = $1",
        grievance_id
    )
    
    if grievance and grievance['user_id']:
        status_messages = {
            'IN_PROGRESS': f"Your grievance {grievance_id} is now being processed.",
            'RESOLVED': f"Your grievance {grievance_id} has been resolved. Please provide feedback."
        }
        
        message = status_messages.get(new_status, f"Grievance {grievance_id} status updated to {new_status}")
        await create_notification(grievance['user_id'], message)
