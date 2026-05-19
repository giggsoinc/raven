# APEXlang Constitutional Master — Prompt Skeletons

Purpose
- Use these skeletons to run the single‑run master workflow that orchestrates:
  - Agent 1 — Draft (generate .apx using rules + templates inside the transient temp workspace)
  - Agent 2 — Critique (rule‑based review checklist with citations and confidence scoring)
  - Agent 3 — Revision (apply accepted fixes and publish after gates pass)
- Master workflow: references/workflows/apex-generation.md

How to use
1) Trigger the master (Message 1):
   references/workflows/apex-generation.md
2) Choose one of two paths:
   - **Natural prompt (recommended):** Type a conversational request (e.g., “When the employee dialog closes, refresh the interactive report”). The NLU router will map it to components, ask for specifics only when needed, and build the structured payload automatically.
   - **Structured payload:** Copy one of the skeleton Message 2 blocks below and fill in the placeholders when you already know every detail.

General template (copy/paste and fill)
- Message 1:
  references/workflows/apex-generation.md

- Message 2:
  target_type: <application|page|form|interactive-report|chart|dashboard|items|templates|dynamic-action>
  intent: <short description of the goal, what to build and how it’s used>
  data_contract:
    # Describe required tables/views, primary keys, columns; and lov mapping when needed
    # Example:
    # emp:
    #   table: EMP
    #   pk: EMPNO
    #   cols: [EMPNO, ENAME, JOB, MGR, HIREDATE, SAL, COMM, DEPTNO]
    # dept:
    #   table: DEPT
    #   pk: DEPTNO
    #   cols: [DEPTNO, DNAME, LOC]
    #   lov: value=DEPTNO, display=DNAME
  output_path: applications/app_###/

One‑liner usage (optional — NLU Router)
- A single natural sentence is enough (e.g., “Add a dynamic action that disables Commission unless Job = SALESMAN”). The router will:
  - Detect components via assets/apex-generation/components.registry.json
  - Compute target_type (single component → that type; multiple → page)
  - Co‑load the correct rules via assets/rules-mapping.json
  - Choose page patterns from `templates/page-examples/**` first for page-scoped work
  - Choose only templates under templates/*
  - Never use `applications/**` as a pattern or scaffold source
  - Ask for missing inputs (PK, columns, LOV mapping) without inventing values

Guardrails (always enforced)
- Minimal rule loading via assets/rules-mapping.json:
  - 00‑guard → 10‑global → relevant 20/30/40
- Do not invent attributes or CSS classes (use templates/* and 40-components/apex.templates.md)
- Do not use `applications/**` as an example corpus; read the resolved target app only for concrete integration facts
- In every generated `.apx` artifact, emit one top-level declaration per block and separate sibling top-level declarations with a blank line. Never place two sibling declarations on the same line.
- SQL must be in triple backticks (multi‑line strings)
- Heavy logic in DB packages/views; prefer declarative validations/processes; guard DML by button
- If required inputs (e.g., PK) are missing, the system records “Missing Inputs”; no fabrication

Artifacts produced
- Working copy: transient temp workspace outside the repo
- Durable runtime evidence: compact report + transcript under `the temp-runtime logs directory under `APEXLANG_OUTPUT_ROOT/logs/`` when the workflow reaches runtime gates or explicitly persists logs
- Final:
  - For page or page-based component runs: `applications/app_###/pages/...`
  - For shared-component runs: `applications/app_###/shared-components/...`
  - For whole application runs: `applications/app_###/` where `###` is the next available zero-padded sequence (e.g., `app_001`, `app_002`, ...)
- output_path? (defaults per scope)
    - Sequence computation: scan applications/ for existing app_* folders and pick the next integer.
Skeletons by target_type

A) Page — Blank page with Static Region (smoke test)
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: page
  intent: Create a blank page with one Static Region titled Hello APEX
  data_contract: none
  output_path: applications/app_###/
- Template refs: templates/page-examples/blank-page/blank-page._index.md, templates/region-components/static-content/static-content._common.md

B) Interactive Report — EMP with Department filter (Select List LOV)
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: interactive-report
  intent: Build an IR on EMP with a Select List filter on DEPTNO populated from Departments LOV
  data_contract:
    emp:
      table: EMP
      pk: EMPNO
      cols: [EMPNO, ENAME, JOB, MGR, HIREDATE, SAL, COMM, DEPTNO]
    dept:
      table: DEPT
      pk: DEPTNO
      cols: [DEPTNO, DNAME, LOC]
      lov: value=DEPTNO, display=DNAME
  styling: none
  output_path: applications/app_###/
- Template refs: templates/page-examples/interactive-report-page/interactive-report-page._index.md, templates/items/select-list/select-list._index.md, templates/shared-components/lovs/lovs.dynamic.query.md

C) Modal CRUD Form — EMP (invoked from IR row)
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: form
  intent: Modal CRUD form on EMP (create/edit/delete), invoked from IR row; use Departments LOV for DEPTNO
  data_contract:
    emp:
      table: EMP
      pk: EMPNO
      cols: [EMPNO, ENAME, JOB, MGR, HIREDATE, SAL, COMM, DEPTNO]
    dept:
      table: DEPT
      pk: DEPTNO
      cols: [DEPTNO, DNAME, LOC]
      lov: value=DEPTNO, display=DNAME
  styling: none
  output_path: applications/app_###/
- Template refs: templates/page-examples/form-page/form-page._index.md, templates/items/select-list/select-list._index.md

D) Dashboard — Two tiles or charts (Headcount and Salary by Department)
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: dashboard
  intent: Dashboard with two visuals — Headcount by Department and Salary by Department
  data_contract:
    emp:
      table: EMP
      pk: EMPNO
      cols: [EMPNO, ENAME, JOB, MGR, HIREDATE, SAL, COMM, DEPTNO]
    dept:
      table: DEPT
      pk: DEPTNO
      cols: [DEPTNO, DNAME, LOC]
  styling: none
  output_path: applications/app_###/
- Template refs: templates/page-examples/dashboard-page/dashboard-page._index.md, templates/page-examples/classic-report-page/classic-report-page._index.md (or charts via apex.charts page rules)

E) Chart — Single chart (Salary by Department)
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: chart
  intent: Build a chart showing Salary by Department
  data_contract:
    emp:
      table: EMP
      pk: EMPNO
      cols: [EMPNO, ENAME, JOB, MGR, HIREDATE, SAL, COMM, DEPTNO]
    dept:
      table: DEPT
      pk: DEPTNO
      cols: [DEPTNO, DNAME, LOC]
  styling: none
  output_path: applications/app_###/
- Page rules: references/policies/memory-bank/30-pages/apex.chart-page.md

F) Items — Departments LOV (shared component)
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: items
  intent: Create a shared LOV “Departments” mapping DEPTNO → DNAME
  data_contract:
    dept:
      table: DEPT
      pk: DEPTNO
      cols: [DEPTNO, DNAME, LOC]
      lov: value=DEPTNO, display=DNAME
  styling: none
  output_path: applications/app_###/
- Template refs: templates/shared-components/lovs/lovs.dynamic.query.md, templates/shared-components/lovs/lovs.dynamic.query.md

G) Dynamic Action — Refresh region after modal closes
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: dynamic-action
  intent: Refresh the EMP_IR region after the EMP_FORM dialog closes
  data_contract:
    page: Departments overview (page 10)
    modal_region: EMP_FORM_DIALOG
    report_region: EMP_IR
  styling: none
  output_path: applications/app_###/
- Template refs: templates/business-logic/dynamic-actions/dynamic-actions.refresh-region-after-dialog.md

H) Dynamic Action — Debounce/Throttle text updates
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: dynamic-action
  intent: Mirror textarea value into a display-only item using execution control timing
  data_contract:
    page: Live typing diagnostics (page 21)
    source_item: P21_TEXT_AREA
    target_items: P21_DEBOUNCE_DELAY
    execution:
      type: debounce
      time: 600
      immediate: false
  styling: none
  output_path: applications/app_###/
- Template refs: templates/business-logic/dynamic-actions/dynamic-actions.execution-debounce-throttle.md

I) Dynamic Action — Delete row via invokeApi
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: dynamic-action
  intent: Delete an employee row from report EMP_IR when clicking delete icon and show success notification
  data_contract:
    page: Delete employees (page 18)
    jquerySelector: a.delete-row
    delete_item: P18_DELETE_PK
    api: app_process_api.delete_emp
    target_region: EMP_IR
  styling: none
  output_path: applications/app_###/
- Template refs: templates/business-logic/dynamic-actions/dynamic-actions.delete-with-notification.md

J) Page scaffolding — Blank page with Breadcrumb region
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: page
  intent: Blank page with Breadcrumb region and proper breadcrumb entry
  data_contract: none
  styling: none
  output_path: applications/app_###/
- Template refs: templates/page-examples/blank-page/blank-page._index.md, templates/shared-components/breadcrumbs/breadcrumb-entries.md

K) Application slice (Tier‑2 orchestration guidance)
- If you need multiple pages and shared components wired together (e.g., IR → Modal Form + Dashboard), run repeated master invocations through `references/workflows/apex-generation.md` so each artifact stays under the same `applications/app_###/` root with full Draft → Critique → Revision enforcement.

L) Page — Interactive Report + Form (same page)
- Message 1:
  references/workflows/apex-generation.md
- Message 2:
  target_type: page
  intent: Build a single page containing two regions — an Interactive Report (list) and a Form (detail). The Interactive Report lists EMP records; the Form edits the selected EMP record on the same page. Guard DML by button, and add a dynamic action to refresh the IR after form submit.
  data_contract:
    emp:
      table: EMP
      pk: EMPNO
      cols: [EMPNO, ENAME, JOB, MGR, HIREDATE, SAL, COMM, DEPTNO]
    dept:
      table: DEPT
      pk: DEPTNO
      cols: [DEPTNO, DNAME, LOC]
      lov: value=DEPTNO, display=DNAME
  styling: none
  output_path: applications/app_###/
- Template refs: templates/page-examples/interactive-report-page/interactive-report-page._index.md, templates/page-examples/form-page/form-page._index.md, templates/business-logic/dynamic-actions/dynamic-actions.refresh-region-after-dialog.md, templates/shared-components/lovs/lovs.dynamic.query.md

Test matrix (examples → expected routing)
- “Page with an interactive report and a form on EMP; use Departments LOV for DEPTNO; refresh report after submit”
  - Components: [interactive report, form, lov, dynamic action refresh]
  - target_type: page
  - Rules: page + interactive-report + form + logic + items/sql
- Templates: region-components/interactive-report/interactive-report._common.md, region-components/form/form._common.md, shared-components/lovs/lovs.dynamic.query.md, business-logic/dynamic-actions/dynamic-actions.refresh-region-after-dialog.md
- “Dashboard with cards summarizing headcount by department”
  - Components: [dashboard/cards]
  - target_type: page (or dashboard)
  - Rules: page + dashboard
  - Templates: dashboard.apx (optionally classic-report.apx)
- “Add a calendar of EMP hires”
  - Components: [calendar]
  - target_type: page
  - Rules: page
  - Templates: calendar.apx
  - Ask: date column (e.g., HIREDATE)
- “Create a map for office locations”
  - Components: [map]
  - target_type: page
  - Rules: page
  - Templates: map.apx
  - Ask: lat/long columns or geocode

Composition notes
- Shared template, label, grid, and framing defaults come from references/policies/memory-bank/40-components/apex.templates.md
- Prefer template and layout attributes over class-based adjustments

Troubleshooting
- Missing inputs (e.g., PK not specified) → Critique calls out “Missing Inputs”; Revision will not fabricate
- Ambiguous target_type (mixed page types in one run) → Guard asks for clarification before drafting
- DB policy enforcement → If db.connection rules are missing/ambiguous, DML/process generation is blocked until clarified
