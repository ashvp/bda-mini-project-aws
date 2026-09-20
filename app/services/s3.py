import os
import uuid
import logging
from typing import Set
from fastapi import UploadFile, HTTPException, status
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_image_file(file: UploadFile) -> str:
    """Validate image extension and content type, returning the normalized extension."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename."
        )

    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        )

    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type '{file.content_type}'. Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    return ext


def get_s3_client():
    """Build boto3 S3 client using environment settings."""
    kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


async def upload_maintenance_image(file: UploadFile) -> str:
    """
    Uploads an image either to AWS S3 (production) or local directory (local mock).
    Returns the public image URL.
    """
    ext = validate_image_file(file)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    s3_key = f"maintenance-images/{unique_name}"

    # Check file size by reading in chunks or seek
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    # Local mock mode for development or when credentials are not supplied
    if settings.USE_LOCAL_S3_MOCK or not (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY):
        upload_dir = settings.LOCAL_UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        local_path = os.path.join(upload_dir, unique_name)
        with open(local_path, "wb") as f:
            f.write(content)
        logger.info(f"Saved image locally: {local_path}")
        return f"/uploads/{unique_name}"

    # Real AWS S3 upload
    try:
        s3 = get_s3_client()
        content_type = file.content_type or "image/jpeg"

        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=s3_key,
            Body=content,
            ContentType=content_type
        )
        url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"Uploaded image to S3: {url}")
        return url
    except (ClientError, BotoCoreError) as e:
        logger.error(f"S3 Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload image to AWS S3: {str(e)}"
        )
