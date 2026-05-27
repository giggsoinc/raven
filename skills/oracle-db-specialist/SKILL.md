---
name: oracle-db-specialist
description: Oracle Database guidance for SQL, PL/SQL, SQLcl, ORDS, administration, performance, security, migrations, and agent-safe database workflows. Version-aware across 19c, 21c, and 23ai. Trigger on: SQL, PL/SQL, SQLcl, ORDS, JDBC, node-oracledb, AWR, ASH, explain plan, Data Guard, RAC, Multitenant, Exadata, schema migrations, VPD, auditing, encryption, vector search, SELECT AI, property graph, JSON Relational Duality, OML, True Cache.
---

# Oracle Database Specialist

## Fetch Protocol

All reference guides live at `https://raw.githubusercontent.com/giggsoinc/skills/main/db/`.
Use WebFetch to pull the specific file when a topic matches the routing table.
On network failure: answer from built-in Oracle DB knowledge and note the limitation.

## Category Routing

| Topic | Fetch URL |
|-------|-----------|
| Backup, recovery, RMAN, Data Guard, redo/undo logs, users | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/admin/README.md` |
| Safe DML, destructive guards, idempotency, schema discovery, ORA- errors | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/agent/README.md` |
| JDBC, pooling, JSON, XML, spatial, Oracle Text, MLE, language drivers | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/appdev/README.md` |
| RAC, Multitenant, Exadata, In-Memory, OCI DB services, Data Guard architecture | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/architecture/README.md` |
| OCR database container images and pull guidance | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/containers/container-selection-matrix.md` |
| ERD, data modeling, partitioning, tablespaces | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/design/README.md` |
| Schema migrations, online ops, edition-based redefinition, version control | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/devops/schema-migrations.md` |
| AQ, DBMS_SCHEDULER, materialized views, DBLinks, vector search, SELECT AI | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/features/README.md` |
| SQLAlchemy, Django, Pandas, Spring JPA, MyBatis, TypeORM, Sequelize, GORM | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/frameworks/README.md` |
| Migrations from PostgreSQL, MySQL, SQL Server, MongoDB, Snowflake | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/migrations/migration-assessment.md` |
| Alert log, ADR, health monitor, space management, top SQL | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/monitoring/README.md` |
| ORDS architecture, installation, REST design, auth, monitoring | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/ords/README.md` |
| AWR, ASH, explain plan, indexes, optimizer stats, wait events, memory | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/performance/explain-plan.md` |
| Package design, error handling, collections, cursors, debugging | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/plsql/plsql-package-design.md` |
| Privileges, VPD, masking, auditing, encryption, network security | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/security/README.md` |
| SQL tuning, patterns, dynamic SQL, injection avoidance | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/sql-dev/README.md` |
| SQLcl scripting, Liquibase, DDL gen, MCP server, AWR, background jobs | `https://raw.githubusercontent.com/giggsoinc/skills/main/db/sqlcl/sqlcl-mcp-server.md` |

## Version Capability Matrix

Ask the customer's Oracle version FIRST. Features vary significantly across versions.

| Feature | 19c | 21c | 23ai | Notes |
|---------|-----|-----|------|-------|
| Multitenant | ✅ | ✅ | ✅ | 19c limited to 3 PDBs (free) |
| JSON support | Basic | Native JSON type | JSON Relational Duality | 23ai duality views are game-changing |
| Vector search | ❌ | ❌ | ✅ | VECTOR datatype, DBMS_VECTOR, similarity search |
| SELECT AI | ❌ | ❌ | ✅ | Natural language SQL via AI profiles |
| Property Graph | Basic (PGX) | Basic (PGX) | ✅ SQL/PGQ | 23ai: graph queries in standard SQL |
| In-DB ML (OML) | ✅ | ✅ | ✅ Enhanced | 23ai adds AutoML, ONNX import |
| Edition-Based Redefinition | ✅ | ✅ | ✅ | Zero-downtime schema changes |
| In-Memory | ✅ | ✅ | ✅ | Requires Enterprise Edition + option |
| Blockchain Tables | ❌ | ✅ | ✅ | Immutable rows |
| True Cache | ❌ | ❌ | ✅ | In-memory read-only cache instances |
| ORDS | ✅ 20+ | ✅ | ✅ | REST APIs, version-independent |
| Data Guard | ✅ | ✅ | ✅ | Active Data Guard requires license |
| RAC | ✅ | ✅ | ✅ | Enterprise Edition only |

### Version-Specific Guidance Rules
- Never recommend 23ai features to a 19c customer without flagging the version gap
- Always ask: "Which Oracle version and edition (SE2/EE)?" before architecture advice
- If customer says "latest" → assume 23ai but confirm
- If customer is migrating versions → fetch `migrations/` guides for cross-version considerations
- 19c is in extended support until April 2027 — still widely deployed, never dismiss it

## Common Flows

| Task | Fetch sequence |
|------|----------------|
| Diagnose slow query | `performance/explain-plan.md` → `performance/wait-events.md` → `performance/optimizer-stats.md` |
| Plan a migration | `migrations/migration-assessment.md` → source-specific `migrations/migrate-*.md` |
| Build RAG on Oracle | `features/ai-profiles.md` → `features/vector-search.md` → `features/dbms-vector.md` |
| Agent-safe schema change | `agent/schema-discovery.md` → `agent/destructive-op-guards.md` → `devops/schema-migrations.md` |
| Set up SQLcl MCP | `sqlcl/sqlcl-basics.md` → `security/privilege-management.md` → `sqlcl/sqlcl-mcp-server.md` |

Full source: https://github.com/giggsoinc/skills/tree/main/db
