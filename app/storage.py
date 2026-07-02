"""Object storage for product images (S3-compatible: Cloudflare R2, AWS S3, B2)."""
import uuid

from .config import settings

EXT_BY_TYPE = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def is_configured() -> bool:
    return all([
        settings.s3_endpoint,
        settings.s3_bucket,
        settings.s3_access_key,
        settings.s3_secret_key,
        settings.s3_public_base,
    ])


def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region or "auto",
        config=Config(signature_version="s3v4"),
    )


def upload_image(data: bytes, content_type: str) -> str:
    """Store the bytes and return the public URL."""
    ext = EXT_BY_TYPE.get(content_type, "jpg")
    key = f"products/{uuid.uuid4().hex}.{ext}"
    _client().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )
    return f"{settings.s3_public_base.rstrip('/')}/{key}"
