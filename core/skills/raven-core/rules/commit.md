# Commit Gate Rules

Run in order — any failure = hard block:
1. Manifest present + valid JSON
2. manifest.secrets.json NOT staged
3. No secrets in staged files (api_key, password, AWS_SECRET)
4. All imports CVE-checked (run cve-check.py per lib)
5. No print() statements
6. No file >150 lines
7. File deletions need [GUARD:ALLOW-DELETE] flag
