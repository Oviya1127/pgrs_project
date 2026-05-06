"""Cloudinary upload service for grievance attachments."""
import cloudinary
import cloudinary.uploader
from config import get_settings
from backend.utils import db

settings = get_settings()

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/avi"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB


async def ensure_attachments_table():
    """Create the grievance_attachments table if it doesn't exist."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS grievance_attachments (
            attachment_id SERIAL PRIMARY KEY,
            grievance_id VARCHAR(10) REFERENCES grievances(grievance_id) ON DELETE CASCADE,
            file_url TEXT NOT NULL,
            file_type VARCHAR(10) CHECK (file_type IN ('IMAGE', 'VIDEO')) NOT NULL,
            public_id TEXT NOT NULL,
            original_name VARCHAR(255),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


async def upload_to_cloudinary(file_bytes: bytes, filename: str, content_type: str) -> dict:
    """Upload a file to Cloudinary and return the result."""
    is_video = content_type in ALLOWED_VIDEO_TYPES
    resource_type = "video" if is_video else "image"
    
    result = cloudinary.uploader.upload(
        file_bytes,
        folder="PGRS_PROJECT",
        resource_type=resource_type,
        public_id=None,  # auto-generated
        overwrite=False,
        use_filename=True,
        unique_filename=True
    )
    
    return {
        "url": result.get("secure_url"),
        "public_id": result.get("public_id"),
        "resource_type": resource_type,
        "format": result.get("format"),
        "width": result.get("width"),
        "height": result.get("height"),
    }


async def save_attachment(grievance_id: str, file_url: str, file_type: str, public_id: str, original_name: str) -> dict:
    """Save attachment record to database."""
    result = await db.fetch_one(
        """
        INSERT INTO grievance_attachments (grievance_id, file_url, file_type, public_id, original_name)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING attachment_id, grievance_id, file_url, file_type, original_name, uploaded_at
        """,
        grievance_id, file_url, file_type, public_id, original_name
    )
    return dict(result) if result else None


async def get_attachments(grievance_id: str) -> list:
    """Get all attachments for a grievance."""
    rows = await db.fetch_all(
        """
        SELECT attachment_id, grievance_id, file_url, file_type, original_name, uploaded_at
        FROM grievance_attachments
        WHERE grievance_id = $1
        ORDER BY uploaded_at ASC
        """,
        grievance_id
    )
    return [dict(r) for r in rows]


async def delete_attachment(attachment_id: int, grievance_id: str) -> bool:
    """Delete an attachment from Cloudinary and database."""
    row = await db.fetch_one(
        "SELECT public_id FROM grievance_attachments WHERE attachment_id = $1 AND grievance_id = $2",
        attachment_id, grievance_id
    )
    if not row:
        return False
    
    try:
        cloudinary.uploader.destroy(row["public_id"])
    except Exception:
        pass  # Even if Cloudinary delete fails, remove DB record
    
    await db.execute(
        "DELETE FROM grievance_attachments WHERE attachment_id = $1",
        attachment_id
    )
    return True
