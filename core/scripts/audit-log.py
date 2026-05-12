#!/usr/bin/env python3
# Raven — Audit Logger v4.0
# Cloud-aware: routes to S3, GCS, Azure Blob, OCI, or local
# based on manifest stack.cloud and manifest.secrets.json audit config
# NEVER errors. NEVER blocks. Silent if not configured.

import json, sys, os, re, gzip, base64
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

def build_entry(data, manifest):
    return json.dumps({
        "ts":        datetime.now(timezone.utc).isoformat(),
        "event":     "tool_call",
        "tool":      data.get("tool_name", "unknown"),
        "ok":        data.get("tool_response", {}).get("error") is None,
        "dev":       os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER", "unknown")),
        "github_id": manifest.get("github_id", ""),
        "project":   manifest.get("project", os.path.basename(os.getcwd())),
        "session":   os.environ.get("CLAUDE_SESSION_ID", "")
    })

def detect_provider(manifest, secrets):
    """Detect which cloud provider to use for audit storage."""
    # Explicit config in secrets takes priority
    explicit = secrets.get("audit", {}).get("provider", "")
    if explicit:
        return explicit

    # Fall back to cloud declared in manifest
    cloud = manifest.get("stack", {}).get("cloud", [])
    if isinstance(cloud, str):
        cloud = [cloud]

    # Priority order if multi-cloud
    for c in cloud:
        c = c.lower()
        if c == "aws":     return "s3"
        if c == "gcp":     return "gcs"
        if c == "azure":   return "azure"
        if c == "oci":     return "oci"

    return "local"

def get_fernet(secrets):
    try:
        from cryptography.fernet import Fernet
        key = secrets.get("audit", {}).get("encryption_key", "")
        return Fernet(base64.urlsafe_b64decode(key.encode())) if key else None
    except:
        return None

def make_payload(line, fernet):
    compressed = gzip.compress(line.encode(), compresslevel=9)
    return fernet.encrypt(compressed) if fernet else compressed

def audit_path(manifest, secrets, date_str, fernet):
    project   = manifest.get("project", os.path.basename(os.getcwd()))
    dev       = os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER","unknown"))
    dev_safe  = dev.replace("@","_at_")
    # audit_tag: GitHub ID → project tag → project name (in priority order)
    audit_tag = (manifest.get("github_id","") or
                 manifest.get("audit_tag","") or
                 project)
    ext = ".log.gz.enc" if fernet else ".log.gz"
    return f"raven/{project}/{dev_safe}/{audit_tag}/{date_str}{ext}"

# ── AWS S3 ─────────────────────────────────────────────────────────────────────
def write_s3(line, secrets):
    def _write():
        import boto3
        audit  = secrets.get("audit", {})
        bucket = audit.get("s3_bucket", "")
        if not bucket: return
        region  = audit.get("s3_region", "us-east-1")
        kms_key = audit.get("kms_key_id", "")
        fernet  = get_fernet(secrets)
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(manifest, secrets, date_str, fernet)
        s3      = boto3.client("s3", region_name=region)
        existing = b""
        try:
            raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            existing = gzip.decompress(fernet.decrypt(raw)) if fernet else raw
        except: pass
        payload = make_payload((existing + line.encode()).decode() if existing else line, fernet)
        put_args = {"Bucket": bucket, "Key": key, "Body": payload}
        if kms_key:
            put_args.update({"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": kms_key})
        else:
            put_args["ServerSideEncryption"] = "aws:kms"
        s3.put_object(**put_args)
    safe(_write)

# ── Google Cloud Storage ───────────────────────────────────────────────────────
def write_gcs(line, secrets):
    def _write():
        from google.cloud import storage
        audit  = secrets.get("audit", {})
        bucket = audit.get("gcs_bucket", "")
        if not bucket: return
        fernet  = get_fernet(secrets)
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(manifest, secrets, date_str, fernet)
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

# ── Azure Blob Storage ─────────────────────────────────────────────────────────
def write_azure(line, secrets):
    def _write():
        from azure.storage.blob import BlobServiceClient
        audit  = secrets.get("audit", {})
        conn   = audit.get("azure_connection_string", "")
        cont   = audit.get("azure_container", "")
        if not conn or not cont: return
        fernet  = get_fernet(secrets)
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(manifest, secrets, date_str, fernet)
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

# ── OCI Object Storage ─────────────────────────────────────────────────────────
def write_oci(line, secrets):
    def _write():
        import oci, io
        audit      = secrets.get("audit", {})
        namespace  = audit.get("oci_namespace", "")
        bucket     = audit.get("oci_bucket", "")
        if not namespace or not bucket: return
        fernet  = get_fernet(secrets)
        date_str= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key     = audit_path(manifest, secrets, date_str, fernet)
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

# ── Local fallback ─────────────────────────────────────────────────────────────
def write_local(line, secrets):
    def _write():
        if not secrets.get("audit", {}).get("local_fallback", False): return
        os.makedirs(".raven/audit", exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        open(f".raven/audit/fallback-{date_str}.log","a").write(line+"\n")
    safe(_write)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    data = safe(lambda: json.load(sys.stdin)) or {}
    manifest, secrets = load_config()
    line = REDACT.sub(r'\1:[REDACTED]', build_entry(data, manifest))

    provider = detect_provider(manifest, secrets)

    if   provider in ("s3",  "aws"):   write_s3(line, secrets)
    elif provider in ("gcs", "gcp"):   write_gcs(line, secrets)
    elif provider == "azure":          write_azure(line, secrets)
    elif provider == "oci":            write_oci(line, secrets)

    # Always try local fallback regardless of provider (if enabled)
    write_local(line, secrets)
    sys.exit(0)

if __name__ == "__main__":
    main()
