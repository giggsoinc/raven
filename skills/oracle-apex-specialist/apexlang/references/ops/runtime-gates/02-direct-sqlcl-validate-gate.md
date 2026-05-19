> All `node tools/apexctl.mjs ...` commands are package-root relative: run them from the packaged skill root, or invoke that script by explicit path.

# Agent: Direct SQLcl Validate Gate

Purpose
- Provide the canonical live-runtime gate for APEXlang artifact workflows.
- Enforce direct SQLcl `apex validate` before any optional import.
- Block completion until the live APEXLang check is proven; import eligibility is proven only after an explicit post-check import choice.

Scope
- Applies to all APEXlang-producing skills that generate or modify application artifacts.
- Excluded: requests that do not enter APEXlang artifact-generation workflows.

Preconditions
- Target artifacts were produced by the internal generate -> review -> fix loop in the transient temp workspace.
- `resolved_app_path` is absolute and points to the application folder being changed.
- `db_connection_name` is resolved for this run.
- The corresponding APEX workspace name is resolved for this run.
- Runtime capability status is resolved for this run.

Runtime contract
- Use direct SQLcl commands only.
- Default to `validate-only` for every APEX artifact workflow before the live SQLcl session begins.
- After the live APEXLang check passes, offer GUI/clickable choices: `Check APEXLang code` (recommended) or `Check and import APEXLang code`; include a short purpose summary and, if GUI choices are unavailable, stop after checking the code and report import as a follow-up.
- Probe both supported runtime paths and select the live runtime path before validate/import:
  - resolved build-root runtime via `apex sql`
  - PATH SQLcl runtime via `sql <db_connection_name>` or `sql /nolog` plus `connect <db_connection_name>`
- `apex validate -input <resolved_app_path>` is mandatory for every live runtime run.
- `validate-and-import` runs for existing apps must resolve and preserve a canonical live numeric application id before any import-authorized continuation.
- If staged deployment metadata does not match that canonical application id, reconcile `resolved_app_path` to the canonical target before import.
- If the post-check GUI choice resolves to import, `apex validate -input <resolved_app_path>` and `apex import -input <resolved_app_path>` must run in the same authenticated SQLcl user session.
- The session must use the same `db_connection_name`, workspace context, and effective SQLcl user.
- If the session changes between validate and import, STOP and re-run validation before import.
- Do not replace the live validate/import path with Python wrapper scripts when direct SQLcl commands are available.
- If SQLcl explicitly reports multiple-workspace ambiguity, resolve the workspace id automatically for the active `db_connection_name` and restart the same real-SQLcl sequence with a run-scoped explicit `-workspaceid`.

Execution
1. Run the local first-pass check using `node tools/apexctl.mjs apexlang validate --app-path <resolved_app_path>`.
2. Treat any validator failure from that command as blocking before live SQLcl work.
3. If the npm wrapper fails before validator startup, the runtime may use the direct internal validator entrypoint as a same-path fallback, but it must report that fallback explicitly and must not use it to bypass real validator findings.
4. Persist the compact runtime JSON report and transcript under `the temp-runtime logs directory under `APEXLANG_OUTPUT_ROOT/logs/``.
5. If any local validator fails, stop and surface every reported finding before any SQLcl import attempt.
6. Run `node tools/apexctl.mjs runtime preflight --db-connection-name <db_connection_name>` and stop before live runtime work unless the report confirms validate/import capability.
7. Attempt the live APEXLang check at most 3 times in one run.
8. For each attempt, use the selected real runtime path and keep validate/import in the same authenticated SQLcl session.
9. Run `apex validate -input <resolved_app_path>` in that session.
10. If SQLcl reports multiple-workspace ambiguity, resolve the workspace id automatically for the active `db_connection_name` and restart that attempt with an explicit `-workspaceid` for the active run.
11. After live validate passes, run runtime UI verification for changed pages before any import continuation. Prefer Chrome DevTools MCP when the caller provides it; otherwise use the runtime verifier's inferred page URLs plus HTTP/HTML artifacts.
12. Treat critical runtime verification findings such as login redirects, HTTP failures, APEX/ORA error text, or missing live state needed for the active fix as blocking. Route them through debugging before any import attempt.
13. If a build-root runtime attempt fails before real `apex validate` / `apex import` output because of sandbox-only filesystem/setup errors such as `EPERM`, `ENOENT`, or build-root `workdir/*` write failures, classify the result as an environment blocker, do not consume the 3-attempt validate budget, do not route to the debugging/fix loop, and continue with the real live build-root roundtrip in an execution context that can write the required build-root work files.
14. If validate fails with a real SQLcl/compiler outcome, route to `references/domains/README.md`, apply the smallest concrete fix, rerun local validators, and then begin the next attempt in a fresh real SQLcl session.
15. Record `resolved_app_path` as the canonical validated path only after a validate pass.
16. Mark import eligibility only when the live APEXLang check and runtime verification both succeed in that session and the post-check GUI choice resolves to import.

Outputs
- direct SQLcl validate success for the resolved app path
- same-session eligibility for direct SQLcl import when the post-check GUI choice resolves to import
- recorded SQLcl capability status for the run
- recorded command outcome in the run report and transcript

Failure handling
- Local validator failure: stop and surface actionable findings from the local validator output.
- Sandbox-only build-root filesystem/setup blocker before real validate/import output: stop the sandbox attempt, keep the run out of the debugging/fix loop, and continue in a real live build-root execution context without consuming validate-attempt budget.
- Validation failure with a real SQLcl/compiler outcome: route to debugging, then retry from a fresh real SQLcl session until the third failed validate attempt.
- Third failed validate attempt: stop and surface actionable findings plus the owning layer.
- Path mismatch: stop before import.
- Session mismatch: stop and require re-validation.

Notes
- This gate standardizes completion checks; it does not replace domain routing.
- Completion remains blocked until runtime status proves eligibility.
