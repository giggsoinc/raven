# raven_status

Check that Raven is active and the project manifest is valid.

## Usage

```
Run raven_status
```

## What it checks

- `.raven/manifest.json` loaded and valid
- Stack declared
- Secrets file present
- Raven version and mode

## Expected output

```
✅ manifest.json loaded
✅ stack declared
✅ secrets file present
Version: 2.8
Mode: active
```

If anything is missing, Raven will tell you exactly what to fix.
