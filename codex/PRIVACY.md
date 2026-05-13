# Privacy Policy — Raven-Codex

**Giggso Inc** — MIT License

## What Raven collects

Raven operates entirely within your local environment and your own repositories.

- **Audit logs** — stored locally in `.raven/audit/` within your project. Encrypted with your own key (`RAVEN_AUDIT_KEY`). Never sent to Giggso.
- **CVE scan requests** — if `OPENAI_API_KEY` is configured, library names are sent to the OpenAI API for CVE analysis. No source code is sent.
- **Secret scan** — runs locally only. Secret values are never logged or transmitted.
- **Manifest** — stored in `.raven/manifest.json` in your repo. Contains project metadata you provide during setup.

## What Raven does NOT collect

- Source code
- Secret values (keys, passwords, tokens)
- Personal data beyond the email you provide during setup (used for audit trail only, stored locally)
- Usage telemetry

## Third-party services

- **OpenAI API** — used for CVE deep scan only, if you configure your own API key. Subject to [OpenAI's privacy policy](https://openai.com/privacy).

## Contact

giggso.ravi@gmail.com
