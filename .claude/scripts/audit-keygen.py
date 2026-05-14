#!/usr/bin/env python3
# Raven — Audit Key Generator
# Run ONCE on init. Add output to manifest.secrets.json audit.encryption_key
# This key encrypts audit logs before S3 upload.
# Enterprise stores this key in Vault / Secrets Manager.
# Usage: python3 audit-keygen.py

try:
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())
except ImportError:
    print("Install first: pip install cryptography --break-system-packages")
    exit(1)
