# raven_secret_scan

Detect secrets, API keys, credentials, and tokens in changed files before they are committed.

## Usage

```
Run raven_secret_scan
Run raven_secret_scan on config.py
```

## What it detects

- API keys (OpenAI, AWS, GCP, Stripe, Twilio, GitHub tokens)
- Hardcoded passwords and connection strings
- Private keys (RSA, EC, PEM blocks)
- JWT tokens
- Database credentials in code

## Output

```
🔴 SECRET DETECTED: config.py line 12
   Pattern: OpenAI API key
   Action: Move to environment variable — do NOT commit
```

Raven never logs the secret value itself — only the location and pattern type.
