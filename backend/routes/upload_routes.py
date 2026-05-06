"""Upload routes for grievance attachments."""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from backend.middleware import get_current_user
from backend.services.upload_service import (
    upload_to_cloudinary, save_attachment, get_attachments, delete_attachment,
    ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES, MAX_IMAGE_SIZE, MAX_VIDEO_SIZE
)

router = APIRouter(prefix="/grievances", tags=["Attachments"])


@router.post("/{grievance_id}/attachments")
async def upload_attachment(
    grievance_id: str,
    files: List[UploadFile] = File(...),
    current_user=Depends(get_current_user)
):
    """Upload images or videos for a grievance."""
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 files per upload"
        )
    
    uploaded = []
    errors = []
    
    for file in files:
        content_type = file.content_type or ""
        
        if content_type not in ALLOWED_IMAGE_TYPES and content_type not in ALLOWED_VIDEO_TYPES:
            errors.append(f"{file.filename}: Unsupported file type ({content_type})")
            continue
        
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        is_video = content_type in ALLOWED_VIDEO_TYPES
        max_size = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE
        if file_size > max_size:
            limit_mb = max_size // (1024 * 1024)
            errors.append(f"{file.filename}: File too large (max {limit_mb}MB)")
            continue
        
        try:
            cloud_result = await upload_to_cloudinary(file_bytes, file.filename, content_type)
            
            file_type = "VIDEO" if is_video else "IMAGE"
            attachment = await save_attachment(
                grievance_id=grievance_id,
                file_url=cloud_result["url"],
                file_type=file_type,
                public_id=cloud_result["public_id"],
                original_name=file.filename or "unnamed"
            )
            
            if attachment:
                uploaded.append(attachment)
        except Exception as e:
            errors.append(f"{file.filename}: Upload failed - {str(e)}")
    
    return {
        "success": True,
        "message": f"{len(uploaded)} file(s) uploaded successfully",
        "data": {
            "uploaded": uploaded,
            "errors": errors
        }
    }


@router.get("/{grievance_id}/attachments")
async def list_attachments(
    grievance_id: str,
    current_user=Depends(get_current_user)
):
    """Get all attachments for a grievance."""
    attachments = await get_attachments(grievance_id)
    return {
        "success": True,
        "data": attachments
    }


@router.delete("/{grievance_id}/attachments/{attachment_id}")
async def remove_attachment(
    grievance_id: str,
    attachment_id: int,
    current_user=Depends(get_current_user)
):
    """Delete an attachment."""
    deleted = await delete_attachment(attachment_id, grievance_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    return {"success": True, "message": "Attachment deleted"}
