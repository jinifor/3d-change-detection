from functools import lru_cache
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageClient:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
            use_ssl=settings.minio_secure,
        )
        self.presign_client = boto3.client(
            "s3",
            endpoint_url=settings.minio_external_endpoint or settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
            use_ssl=settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=settings.minio_bucket)
        except ClientError:
            self.client.create_bucket(Bucket=settings.minio_bucket)

    def presigned_put_url(self, object_key: str) -> str:
        return self.presign_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.minio_bucket, "Key": object_key},
            ExpiresIn=settings.upload_presign_expires_seconds,
        )

    def presigned_get_url(self, object_key: str) -> str:
        return self.presign_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.minio_bucket, "Key": object_key},
            ExpiresIn=settings.upload_presign_expires_seconds,
        )

    def create_multipart_upload(self, object_key: str) -> str:
        response = self.client.create_multipart_upload(
            Bucket=settings.minio_bucket,
            Key=object_key,
        )
        return str(response["UploadId"])

    def presigned_upload_part_url(
        self,
        object_key: str,
        upload_id: str,
        part_number: int,
    ) -> str:
        return self.presign_client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": settings.minio_bucket,
                "Key": object_key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=settings.upload_presign_expires_seconds,
        )

    def complete_multipart_upload(
        self,
        object_key: str,
        upload_id: str,
        parts: list[dict],
    ) -> None:
        self.client.complete_multipart_upload(
            Bucket=settings.minio_bucket,
            Key=object_key,
            UploadId=upload_id,
            MultipartUpload={
                "Parts": [
                    {"PartNumber": part["part_number"], "ETag": part["etag"]}
                    for part in sorted(parts, key=lambda item: item["part_number"])
                ]
            },
        )

    def download_file(self, object_key: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(settings.minio_bucket, object_key, str(path))

    def upload_file(self, path: Path, object_key: str) -> None:
        self.client.upload_file(str(path), settings.minio_bucket, object_key)

    def delete_prefix(self, prefix: str) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.minio_bucket, Prefix=prefix):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if objects:
                self.client.delete_objects(
                    Bucket=settings.minio_bucket,
                    Delete={"Objects": objects},
                )


@lru_cache
def get_storage_client() -> StorageClient:
    return StorageClient()
