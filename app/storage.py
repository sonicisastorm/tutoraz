"""
File storage helper for course content (videos, thumbnails, homework).

MVP: saves to local disk under app/static/uploads/.
PRODUCTION: swap save_file() to upload to AWS S3 + serve via CloudFront.
The function signatures below are designed so only this file needs to change —
routes call save_file()/delete_file() and never touch disk/S3 directly.

To switch to S3 later:
  1. pip install boto3 (already in requirements-prod.txt)
  2. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET, AWS_CLOUDFRONT_DOMAIN env vars
  3. Replace the body of save_file()/delete_file() with boto3 client calls (see comments below)
"""
import os
import uuid
from flask import current_app

ALLOWED_VIDEO_EXT = {"mp4", "mov", "webm", "avi", "mkv"}
ALLOWED_IMAGE_EXT  = {"png", "jpg", "jpeg", "webp"}
ALLOWED_DOC_EXT    = {"pdf", "doc", "docx"}


def _upload_dir(subfolder):
    path = os.path.join(current_app.root_path, "static", "uploads", subfolder)
    os.makedirs(path, exist_ok=True)
    return path


def _ext_ok(filename, allowed):
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[-1].lower() in allowed


def save_file(file_storage, subfolder, allowed_extensions):
    """
    Save an uploaded file. Returns the public URL, or None if invalid/missing.

    PRODUCTION (S3) VERSION — replace body with:
        import boto3
        s3 = boto3.client("s3")
        key = f"{subfolder}/{uuid.uuid4().hex}.{ext}"
        s3.upload_fileobj(file_storage, current_app.config["AWS_S3_BUCKET"], key,
                           ExtraArgs={"ContentType": file_storage.mimetype})
        return f"https://{current_app.config['AWS_CLOUDFRONT_DOMAIN']}/{key}"
    """
    if not file_storage or file_storage.filename == "":
        return None
    if not _ext_ok(file_storage.filename, allowed_extensions):
        return None

    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = _upload_dir(subfolder)
    file_storage.save(os.path.join(folder, filename))
    return f"/static/uploads/{subfolder}/{filename}"


def delete_file(url, subfolder):
    """
    Delete a previously saved file given its public URL.

    PRODUCTION (S3) VERSION — replace body with:
        import boto3
        s3 = boto3.client("s3")
        key = url.split(f"{current_app.config['AWS_CLOUDFRONT_DOMAIN']}/")[-1]
        s3.delete_object(Bucket=current_app.config["AWS_S3_BUCKET"], Key=key)
    """
    if not url:
        return
    filename = url.rsplit("/", 1)[-1]
    path = os.path.join(_upload_dir(subfolder), filename)
    if os.path.exists(path):
        os.remove(path)
