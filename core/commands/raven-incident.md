---
name: raven-incident
description: Use to create a manual incident report for Guard events
  or production issues. Classifies as P1/P2/P3 and notifies Prism7.
---

# /incident

Usage: /incident {p1|p2|p3} {description}

Steps:
1. Read .shay-rolls/manifest.secrets.json for inbox + escalation
2. Classify severity from argument
3. Generate incident record:
   - ID: INC-{timestamp}
   - Severity: {P1|P2|P3}
   - Description: {description}
   - Reported by: {git config user.email}
   - SLA: P1=15min P2=60min P3=24h
4. Output incident record
5. Instruct: "Send to {shared_inbox} and log to audit trail"
