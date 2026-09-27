# Do not share — Jev uses for Raven

Private note for the `jev` branch. Not a user-facing README.

Jev answers closed questions. It does not write code, edit files, or call tools. Raven acts on the answer.

## Useful to the person using Raven

Beyond model tier, specialist, secret, and risk:

- **Approval.** `noul`: did this message say go ahead, approved, or proceed? That sets the educate write gate without another keyword list.
- **Cost.** `choice`: answer here, or call the expensive model. Short facts never wake the large model.
- **Memory card.** `choice`: is this sentence an open question, a decision, or noise? Only the first two are written to the Obsidian hub.
- **Commit label.** `choice`: docs, fix, or feat, taken from the diff summary. The user still confirms the message.
- **Incident page.** `choice`: P1, P2, or P3 from the report text, using the existing severity table. Notify still uses the secrets file Raven already has.
- **Install help.** `choice`: the user is stuck on setup, or they are asking to change the project. Setup answers stay short and do not open the repo.

## Do not send to Jev

- `.raven/manifest.secrets.json`, API keys, tokens, passwords
- `.env`, private keys, webhook URLs
- Customer data, raw production logs with identifiers
- The key page password field, or any value typed into it

If a `noul` says the prompt itself holds a secret, route `LOCAL_ONLY` and do not include that prompt in the System 1 `state`.
