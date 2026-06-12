from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import request
from werkzeug.utils import secure_filename

from source.core.config.config import appConfig


@dataclass
class StoredFile:
    file_name: str
    file_path: str
    file_url: str
    file_type: str
    size_bytes: int
    storage_mode: str


def storage_mode() -> str:
    return str(appConfig.storageMode or "local").lower()


def storage_root() -> Path:
    root = Path(appConfig.storageRoot or "storage")
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[3] / root
    return root


def public_file_url(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    if storage_mode() == "s3" and appConfig.storagePublicBaseUrl:
        return f"{appConfig.storagePublicBaseUrl.rstrip('/')}/{normalized}"
    base_url = (appConfig.publicBaseUrl or request.host_url.rstrip("/")).rstrip("/")
    return f"{base_url}/api/v1/uploads/{normalized}"


def _s3_client():
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 nao instalado para storage S3") from exc

    kwargs = {
        "region_name": appConfig.s3Region or "auto",
        "aws_access_key_id": appConfig.s3AccessKeyId,
        "aws_secret_access_key": appConfig.s3SecretAccessKey,
    }
    if appConfig.s3EndpointUrl:
        kwargs["endpoint_url"] = appConfig.s3EndpointUrl
    return boto3.client("s3", **kwargs)


def upload_file(file, company_id: str, folder: str = "documents") -> StoredFile:
    if not file or not file.filename:
        raise ValueError("Arquivo nao informado")

    original_name = secure_filename(file.filename)
    extension = Path(original_name).suffix.lower()
    timestamp = datetime.utcnow().strftime("%Y/%m/%d")
    unique_name = f"{uuid4().hex}{extension}"
    relative_path = (Path(folder) / str(company_id or "public") / timestamp / unique_name).as_posix()
    content_type = getattr(file, "mimetype", None) or "application/octet-stream"

    if storage_mode() == "s3":
        if not appConfig.s3Bucket:
            raise RuntimeError("JURISFLOW_S3_BUCKET nao configurado")
        file.stream.seek(0)
        _s3_client().upload_fileobj(
            file.stream,
            appConfig.s3Bucket,
            relative_path,
            ExtraArgs={"ContentType": content_type, "ServerSideEncryption": "AES256"},
        )
        size = file.stream.tell()
        return StoredFile(
            file_name=original_name,
            file_path=relative_path,
            file_url=public_file_url(relative_path),
            file_type=extension.replace(".", "").upper() or "FILE",
            size_bytes=size,
            storage_mode="s3",
        )

    target = storage_root() / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    file.save(target)
    return StoredFile(
        file_name=original_name,
        file_path=relative_path,
        file_url=public_file_url(relative_path),
        file_type=extension.replace(".", "").upper() or "FILE",
        size_bytes=target.stat().st_size,
        storage_mode="local",
    )


def signed_download_url(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    if storage_mode() == "s3":
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": appConfig.s3Bucket, "Key": normalized},
            ExpiresIn=int(appConfig.s3PresignExpiresSeconds),
        )
    return public_file_url(normalized)
