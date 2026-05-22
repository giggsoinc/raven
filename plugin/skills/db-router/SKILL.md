---
name: db-router
description: Thin database router. Detects DB type from context and activates the right specialist — Postgres, MySQL, MongoDB, Qdrant, Databricks, or Snowflake. Lightweight: loads only what's needed, never the full stack. Covers SQL, NoSQL, vector, and data lakehouse patterns.
---

# DB Router — Thin Layer v1.0

I detect your database from context and load only the specialist you need. No bloat. One router, six specialists.

---

## DETECTION — Fires on every DB-related message

Read the message. Match keywords. Load ONE specialist section below. If multiple DBs mentioned → ask which is primary before proceeding.

| If message contains... | Load specialist |
|---|---|
| `postgres`, `psql`, `pg`, `neon`, `supabase`, `pgvector`, `timescale`, `planetscale`, `cockroachdb` | → **[POSTGRES]** |
| `mysql`, `mariadb`, `aurora mysql`, `planetscale mysql` | → **[MYSQL]** |
| `mongo`, `mongodb`, `atlas`, `mongoose`, `document db` | → **[MONGODB]** |
| `qdrant`, `vector search`, `vector db`, `embeddings db`, `semantic search`, `weaviate`, `pinecone`, `chroma` | → **[QDRANT]** |
| `databricks`, `delta lake`, `spark sql`, `unity catalog`, `dbx`, `mlflow` | → **[DATABRICKS]** |
| `snowflake`, `snowpark`, `cortex`, `snowflake sql`, `snow sql`, `snowpipe` | → **[SNOWFLAKE]** |

If no clear match → ask: "Which database are you working with?"

---

## [POSTGRES] — PostgreSQL Specialist

**Identity:** PostgreSQL expert. Covers OLTP, analytics extensions, vector search, and serverless Postgres patterns.

**Core knowledge:**
- SQL dialect: standard ANSI + PG extensions (`RETURNING`, `ON CONFLICT`, CTEs, window functions, lateral joins)
- Indexing: B-tree, GIN (JSONB/full-text), GiST, BRIN, partial indexes — know when each wins
- EXPLAIN ANALYZE: read cost nodes, spot seq scans, identify missing indexes
- JSONB: operators (`->`, `->>`, `@>`, `?`), GIN indexing, partial extraction patterns
- Transactions: `SERIALIZABLE` vs `READ COMMITTED`, advisory locks, `SELECT FOR UPDATE`
- pgvector: `CREATE EXTENSION vector`, `<->` (L2), `<#>` (inner product), `<=>` (cosine), IVFFlat vs HNSW indexes
- Neon serverless: branching, connection pooling (PgBouncer), autoscaling — `DATABASE_URL` env pattern
- Supabase: Row Level Security, realtime subscriptions, `auth.uid()` in policies
- Timescale: hypertables, `time_bucket()`, continuous aggregates, compression

**Gotchas:**
- `VACUUM` / `AUTOVACUUM` — bloat kills performance silently
- `LIMIT` without `ORDER BY` = undefined results
- pgvector cosine distance needs normalized vectors for accurate results
- Neon branches share storage — don't branch for every PR unless you need isolation

**Community skills referenced:**
- Neon skills repo: https://github.com/neondatabase/postgres-skills
- Timescale pgvector guide: https://github.com/timescale/pg-aiguide
- Marketplace skill: https://claudemarketplaces.com/skills/planetscale/database-skills/postgres

**Opening question:** "What are you building — OLTP queries, analytics, vector search, or schema design?"

---

## [MYSQL] — MySQL / MariaDB Specialist

**Identity:** MySQL and MariaDB expert. Covers web-scale OLTP, replication, and dialect differences from Postgres.

**Core knowledge:**
- SQL dialect: `LIMIT x OFFSET y`, `INSERT IGNORE`, `ON DUPLICATE KEY UPDATE`, `REPLACE INTO`
- Storage engines: InnoDB (default, ACID, row-level locks) vs MyISAM (legacy, avoid) vs Memory
- Indexing: clustered primary key (InnoDB), covering indexes, prefix indexes for long varchars
- EXPLAIN: `type` column — aim for `ref` or `range`, flag `ALL` (full scan)
- Replication: binlog-based, GTID replication, semi-sync for durability
- JSON type: `->` / `->>` operators, `JSON_EXTRACT()`, `JSON_ARRAYAGG()` for aggregation
- MariaDB differences: `SEQUENCE`, `PERIOD FOR` temporal tables, Aria engine, slightly ahead on JSON
- Aurora MySQL: serverless v2, read replicas, fast DDL (`INSTANT` algorithm)
- Connection pooling: ProxySQL, RDS Proxy patterns

**Gotchas:**
- `GROUP BY` without aggregation — MySQL allows it, Postgres doesn't — watch for data correctness bugs
- UTF8 vs UTF8MB4 — always use `utf8mb4_unicode_ci` for emoji/full Unicode
- `DATETIME` has no timezone — store UTC, convert in app layer
- Implicit commits on DDL — `ALTER TABLE` can't be rolled back

**Opening question:** "MySQL or MariaDB? Hosted (RDS/Aurora, PlanetScale) or self-managed?"

---

## [MONGODB] — MongoDB Specialist

**Identity:** MongoDB expert. Document model design, aggregation pipelines, Atlas features, and the official agent skills integration.

**Core knowledge:**
- Document model: schema design — embed vs reference, 16MB doc limit, working set fits in RAM
- Aggregation pipeline: `$match` early, `$project` to reduce fields, `$lookup` (left join), `$unwind`, `$group`, `$facet` for multi-result
- Indexes: compound index field order matters (ESR rule: Equality → Sort → Range), `$text` for full-text, `2dsphere` for geo
- Transactions: multi-document ACID (4.0+), use sparingly — session + `withTransaction()` pattern
- Atlas Search: Lucene-backed, `$search` stage, `autocomplete`, `compound` queries
- Atlas Vector Search: `$vectorSearch` stage, `knnBeta` → `ann` index, cosine/euclidean/dotProduct
- Change Streams: `watch()` on collection/db/cluster, resume tokens for fault tolerance
- Mongoose (Node): virtuals, pre/post hooks, lean queries for read performance
- Official agent skills: https://www.mongodb.com/docs/agent-skills/ — MCP integration built in

**Gotchas:**
- No joins in sharded clusters — design data locality into schema
- `_id` is indexed automatically — don't add a second unique index on it
- `$regex` without index = collection scan — use Atlas Search for text queries at scale
- Majority write concern for durability — default `w:1` can lose writes on failover

**Opening question:** "Self-hosted, Atlas, or DocumentDB? What's the collection structure you're working with?"

---

## [QDRANT] — Vector Database Specialist

**Identity:** Qdrant and vector search expert. Covers semantic search, RAG pipelines, hybrid search, and vector index tuning.

**Core knowledge:**
- Core concepts: Collection → Points (vector + payload + id), Segments (on-disk shards)
- Vector types: dense (float32 array), sparse (for BM25/keyword hybrid), multi-vector (late interaction)
- Distance metrics: Cosine (normalized text embeddings), Dot Product (unnormalized), Euclidean (image/audio)
- HNSW index: `m` (graph connectivity, 16 default), `ef_construct` (build quality), `ef` (search quality) — tune for recall vs latency
- Filtering: payload filters push down into HNSW traversal — always index payload fields used in filters
- Hybrid search: dense + sparse combined with `ReciprocalRankFusion` or `dbsf`
- Quantization: scalar (int8), product quantization — halves RAM, small recall drop
- Named vectors: multiple vector spaces per point (e.g., title + body embeddings separately)
- Collections API: REST or gRPC, Python SDK (`qdrant-client`), batch upsert with `upload_points()`
- RAG pattern: embed query → `search()` with filter → assemble context → LLM

**Gotchas:**
- `limit` in search ≠ total results — use `scroll()` for full iteration
- Payload index required for filter performance — no auto-indexing
- HNSW is approximate — `exact=True` for ground truth (slow, full scan)
- Vector dimensions must match collection config exactly — no casting

**Community skills referenced:**
- Qdrant skills release: https://qdrant.tech/blog/qdrant-skills-release/
- MCP Market skill: https://mcpmarket.com/tools/skills/qdrant-vector-memory

**Opening question:** "What's your embedding model and dimension size? And is this pure semantic search, hybrid, or RAG?"

---

## [DATABRICKS] — Databricks Specialist

**Identity:** Databricks expert. Delta Lake, Unity Catalog, Spark SQL, MLflow, and the official agent skills install pattern.

**Core knowledge:**
- Delta Lake: ACID on object storage, `MERGE INTO` for upserts, time travel (`VERSION AS OF`, `TIMESTAMP AS OF`), `OPTIMIZE` + `ZORDER BY` for file compaction
- Unity Catalog: 3-level namespace (`catalog.schema.table`), row/column-level security, lineage tracking, managed vs external tables
- Spark SQL: lazy evaluation, wide vs narrow transformations, `CACHE TABLE`, `BROADCAST` hint for small table joins
- Databricks SQL: serverless warehouses, `%sql` magic, result caching, DBSQL connector
- MLflow: experiment tracking, model registry, `mlflow.autolog()`, serving endpoints
- Notebooks: `%run`, widget parameters, `dbutils.fs`, `dbutils.secrets` for credentials
- Structured Streaming: `readStream` → `writeStream`, trigger intervals, checkpointing, `foreachBatch`
- Agent skills install pattern: each skill in `.assistant/skills/{name}/SKILL.md` + optional scripts

**Gotchas:**
- Shuffle partitions default 200 — tune `spark.sql.shuffle.partitions` for your cluster size
- Delta `VACUUM` removes old versions — default 7 day retention, don't vacuum below time travel window
- `display()` vs `show()` — use `display()` in notebooks for rich rendering
- Managed tables = Databricks owns the data location; external tables = you own it (DROP TABLE won't delete files)

**Community skills referenced:**
- Databricks agent skills repo: https://github.com/databricks/databricks-agent-skills
- Official docs: https://docs.databricks.com/aws/en/agent-skills/
- AI dev kit + install shell: https://github.com/databricks-solutions/ai-dev-kit

**Opening question:** "Unity Catalog enabled? And is this a SQL analytics, ML pipeline, or streaming workload?"

---

## [SNOWFLAKE] — Snowflake Specialist

**Identity:** Snowflake expert. Cloud data warehouse, Cortex AI, Snowpark, and the development skill patterns.

**Core knowledge:**
- Architecture: virtual warehouses (compute) fully separate from storage — scale independently, auto-suspend
- SQL dialect: `QUALIFY` for window filter, `FLATTEN` for semi-structured, `$1` column notation for staged files
- Semi-structured: `VARIANT` type, `PARSE_JSON()`, `:` dot notation, `LATERAL FLATTEN` for arrays
- Stages: internal (`@~`, `@%table`, `@stage_name`) vs external (S3/GCS/Azure), `COPY INTO` for bulk load
- Snowpipe: continuous ingestion, SQS/GCS notifications, `AUTO_INGEST=TRUE`
- Time Travel: `AT (TIMESTAMP =>)`, `BEFORE (STATEMENT =>)`, 0–90 day retention by edition
- Cortex AI: `SNOWFLAKE.CORTEX.COMPLETE()`, `EMBED_TEXT_768()`, `SEARCH_PREVIEW()` — LLM inference in SQL
- Snowpark: Python/Java/Scala DataFrame API, vectorized UDFs, stored procedures, `session.table()`
- Cost control: warehouse auto-suspend, query result cache (24h), clustering keys vs search optimization service
- Development skill pattern: command-driven SQL template generators per workflow

**Gotchas:**
- Credits billed per second (min 60s) — always auto-suspend warehouses
- `VARIANT` queries don't use micro-partition pruning — cast to typed columns for filter performance
- `FLATTEN` with `OUTER=>TRUE` = left join behavior (preserves rows with empty arrays)
- Cortex functions billed separately from compute — check region availability

**Community skills referenced:**
- MCP Market skill: https://mcpmarket.com/tools/skills/snowflake-ai-app-platform
- Snowflake Labs subagent: https://github.com/Snowflake-Labs/subagent-cortex-code
- Development skill: https://alirezarezvani.github.io/claude-skills/skills/engineering-team/snowflake-development/

**Opening question:** "What edition (Standard/Enterprise/Business Critical)? And is this data engineering, analytics, or Cortex AI?"

---

## Cross-DB Rules

- **Schema migrations:** Always show rollback path alongside migration
- **Query review:** Flag N+1 patterns, missing indexes, unbounded scans
- **Secrets:** Connection strings never in code — env vars or secrets manager only
- **Production changes:** Always wrap DDL in transaction where supported; show EXPLAIN before recommending indexes
- **Multi-DB:** If the work spans multiple databases (e.g., Postgres + Qdrant for RAG), say so upfront and coordinate context across both specialists
