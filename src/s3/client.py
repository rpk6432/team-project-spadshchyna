import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from config import settings

_session = aioboto3.Session()


@asynccontextmanager
async def _get_client() -> AsyncIterator[Any]:
    async with _session.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    ) as client:
        yield client


async def ensure_bucket() -> None:
    """Create bucket if it does not exist and set public read policy."""

    async with _get_client() as client:
        try:
            await client.head_bucket(Bucket=settings.s3_bucket)
            return

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")

            if error_code not in ("404", "NoSuchBucket", "NotFound"):
                raise

        try:
            await client.create_bucket(Bucket=settings.s3_bucket)

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")

            if error_code not in (
                "BucketAlreadyExists",
                "BucketAlreadyOwnedByYou",
            ):
                raise

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{settings.s3_bucket}/*",
                }
            ],
        }

        await client.put_bucket_policy(
            Bucket=settings.s3_bucket,
            Policy=json.dumps(policy),
        )


async def upload_file(
    key: str,
    data: bytes,
    content_type: str = "image/jpeg",
) -> str:
    """Upload file and return object key."""

    async with _get_client() as client:
        await client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    return key


async def delete_file(key: str) -> None:
    """Delete file from S3."""

    async with _get_client() as client:
        await client.delete_object(
            Bucket=settings.s3_bucket,
            Key=key,
        )


def get_public_url(key: str) -> str:
    """Return public URL for an S3 object."""

    base_url = settings.s3_public_url.rstrip("/")

    return f"{base_url}/{settings.s3_bucket}/{key}"
