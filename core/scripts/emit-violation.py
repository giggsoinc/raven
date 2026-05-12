#!/usr/bin/env python3
# Raven — Violation Emitter v3.0
# Cloud-aware: same provider detection as audit-log.py
# Called by pre-commit hook + Guard agents on violations
# NEVER errors. NEVER blocks. Silent if not configured.
# Usage: python3 emit-violation.py --type secret_detected --severity P1 --detail "..."

import argparse, json, os, sys, gzip, base64, re
from datetime import datetime, timezone

REDACT = re.compile(
    r'(api[_-]?key|password|token|secret)["\s:=]+["\']?[A-Za-z0-9+/._-]{8,}',
    re.IGNORECASE
)

def safe(fn):
    try: return fn()
    except: return None

def load_config():
    manifest = safe(lambda: json.load(open(".raven/manifest.json"))) or {}
    secrets  = safe(lambda: json.load(open(".raven/manifest.secrets.json"))) or {}
    return manifest, secrets

def detect_provider(manifest, secrets):
    explicit = secrets.get("audit", {}).get("provider", "")
    if explicit: return explicit
    cloud = manifest.get("stack", {}).get("cloud", [])
    if isinstance(cloud, str): cloud = [cloud]
    for c in cloud:
        c = c.lower()
        if c == "aws":   return "s3"
        if c == "gcp":   return "gcs"
        if c == "azure": return "azure"
        if c == "oci":   return "oci"
    return "local"

def get_fernet(secrets):
    try:
        from cryptography.fernet import Fernet
        key = secrets.get("audit", {}).get("encryption_key", "")
        return Fernet(base64.urlsafe_b64decode(key.encode())) if key else None
    except: return None

def audit_path(project, dev, date_str, fernet):
    ext = ".log.gz.enc" if fernet else ".log.gz"
    return f"raven/{project}/{dev.replace('@','_at_')}/{date_str}{ext}"

def write_s3(line, secrets, manifest):
    def _write():
        import boto3
        audit   = secrets.get("audit", {})
        bucket  = audit.get("s3_bucket", "")
        if not bucket: return
        region  = audit.get("s3_region", "us-east-1")
        kms_key = audit.get("kms_key_id", "")
        fernet  = get_fernet(secrets)
        project = manifest.get("project", os.path.basename(os.getcwd()))
        dev     = os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER","unknown"))
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(project, dev, date_str, fernet)
        s3      = boto3.client("s3", region_name=region)
        existing = b""
        try:
            raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            existing = gzip.decompress(fernet.decrypt(raw)) if fernet else raw
        except: pass
        combined   = existing + line.encode()
        compressed = gzip.compress(combined, compresslevel=9)
        final      = fernet.encrypt(compressed) if fernet else compressed
        put_args   = {"Bucket": bucket, "Key": key, "Body": final,
                      "ServerSideEncryption": "aws:kms"}
        if kms_key: put_args["SSEKMSKeyId"] = kms_key
        s3.put_object(**put_args)
    safe(_write)

def write_gcs(line, secrets, manifest):
    def _write():
        from google.cloud import storage
        audit  = secrets.get("audit", {})
        bucket = audit.get("gcs_bucket", "")
        if not bucket: return
        fernet  = get_fernet(secrets)
        project = manifest.get("project", os.path.basename(os.getcwd()))
        dev     = os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER","unknown"))
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(project, dev, date_str, fernet)
        client  = storage.Client()
        blob    = client.bucket(bucket).blob(key)
        existing = b""
        try:
            raw = blob.download_as_bytes()
            existing = gzip.decompress(fernet.decrypt(raw)) if fernet else raw
        except: pass
        combined = existing + line.encode()
        payload  = (fernet.encrypt(gzip.compress(combined, compresslevel=9))
                    if fernet else gzip.compress(combined, compresslevel=9))
        blob.upload_from_string(payload)
    safe(_write)

def write_azure(line, secrets, manifest):
    def _write():
        from azure.storage.blob import BlobServiceClient
        audit  = secrets.get("audit", {})
        conn   = audit.get("azure_connection_string", "")
        cont   = audit.get("azure_container", "")
        if not conn or not cont: return
        fernet  = get_fernet(secrets)
        project = manifest.get("project", os.path.basename(os.getcwd()))
        dev     = os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER","unknown"))
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(project, dev, date_str, fernet)
        client  = BlobServiceClient.from_connection_string(conn)
        blob    = client.get_blob_client(container=cont, blob=key)
        existing = b""
        try:
            raw = blob.download_blob().readall()
            existing = gzip.decompress(fernet.decrypt(raw)) if fernet else raw
        except: pass
        combined = existing + line.encode()
        payload  = (fernet.encrypt(gzip.compress(combined, compresslevel=9))
                    if fernet else gzip.compress(combined, compresslevel=9))
        blob.upload_blob(payload, overwrite=True)
    safe(_write)

def write_oci(line, secrets, manifest):
    def _write():
        import oci, io
        audit     = secrets.get("audit", {})
        namespace = audit.get("oci_namespace", "")
        bucket    = audit.get("oci_bucket", "")
        if not namespace or not bucket: return
        fernet  = get_fernet(secrets)
        project = manifest.get("project", os.path.basename(os.getcwd()))
        dev     = os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER","unknown"))
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(project, dev, date_str, fernet)
        config  = oci.config.from_file()
        client  = oci.object_storage.ObjectStorageClient(config)
        existing = b""
        try:
            raw = client.get_object(namespace, bucket, key).data.content
            existing = gzip.decompress(fernet.decrypt(raw)) if fernet else raw
        except: pass
        combined = existing + line.encode()
        payload  = (fernet.encrypt(gzip.compress(combined, compresslevel=9))
                    if fernet else gzip.compress(combined, compresslevel=9))
        client.put_object(namespace, bucket, key, io.BytesIO(payload))
    safe(_write)

def write_local(line, secrets):
    def _write():
        if not secrets.get("audit", {}).get("local_fallback", False): return
        os.makedirs(".raven/audit", exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        open(f".raven/audit/fallback-{date_str}.log","a").write(line+"\n")
    safe(_write)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--type",     required=True)
    p.add_argument("--severity", default="P3")
    p.add_argument("--detail",   default="")
    p.add_argument("--blocked",  action="store_true")
    args = p.parse_args()

    entry = {
        "ts":       datetime.now(timezone.utc).isoformat(),
        "event":    "violation",
        "type":     args.type,
        "severity": args.severity,
        "detail":   args.detail,
        "blocked":  args.blocked,
        "dev":      os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER","unknown")),
        "project":  os.path.basename(os.getcwd())
    }
    line     = REDACT.sub(r'\1:[REDACTED]', json.dumps(entry))
    manifest, secrets = load_config()
    provider = detect_provider(manifest, secrets)

    if   provider in ("s3",  "aws"):   write_s3(line, secrets, manifest)
    elif provider in ("gcs", "gcp"):   write_gcs(line, secrets, manifest)
    elif provider == "azure":          write_azure(line, secrets, manifest)
    elif provider == "oci":            write_oci(line, secrets, manifest)
    write_local(line, secrets)
    sys.exit(0)

if __name__ == "__main__":
    main()
