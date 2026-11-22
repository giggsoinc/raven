---
name: db-router
description: "Pure routing table. Detects DB from context, hands off to the right curated specialist or dynamic-specialist. Carries zero specialist content itself."
---
## ROUTE

| Keywords detected | Hand off to |
|---|---|
| `postgres` `psql` `pg` `neon` `supabase` `pgvector` `timescale` `cockroachdb` | `postgres-specialist` |
| `redis` `valkey` `upstash` `elasticache` `keydb` | `redis-specialist` |
| `oracle` `plsql` `autonomous db` `oracle 23ai` | `oracle-db-specialist` |
| `kafka` `confluent` `redpanda` `msk` | `kafka-specialist` |
| `qdrant` `pinecone` `weaviate` `chroma` `vector search` `vector db` `embeddings db` | `vector-db-specialist` |
| `mysql` `mariadb` `aurora mysql` `planetscale` | `dynamic-specialist` — platform: MySQL |
| `mongo` `mongodb` `atlas` `mongoose` `documentdb` | `dynamic-specialist` — platform: MongoDB |
| `databricks` `delta lake` `spark sql` `unity catalog` `mlflow` | `dynamic-specialist` — platform: Databricks |
| `snowflake` `snowpark` `cortex` `snowpipe` | `dynamic-specialist` — platform: Snowflake |
| `dynamodb` `dynamo` | `dynamic-specialist` — platform: DynamoDB |
| `cassandra` `scylladb` `astra db` | `dynamic-specialist` — platform: Cassandra |
| `sqlite` `libsql` `turso` | `dynamic-specialist` — platform: SQLite |
| anything else | resolve first (see below), then `dynamic-specialist` if unresolved |

Multiple DBs in one message → ask which is primary before routing.

## RESOLVE BEFORE FALLBACK

For any DB keyword not in the table above, run the resolver before assuming no curated skill exists:
Commands for the user to review and run themselves:
```text
python3 scripts/skill-resolve.py "[detected DB name]" --caller db-router
```
- `status: hit` → hand off to the returned skill, not `dynamic-specialist`.
- `status: miss` → the miss is logged to `.raven/audit/skill-misses.jsonl` automatically. Proceed to `dynamic-specialist` — platform: [detected DB name].

## RULES

- Never answer DB questions directly. Always route first.
- Curated specialists carry their own gotchas, syntax, and opening questions.
- `dynamic-specialist` rates MySQL/Mongo/Databricks/Snowflake as HIGH confidence — no search agent needed.
- Cross-DB work (e.g. Postgres + Qdrant for RAG) → route to primary, mention secondary in handoff context.
- Secrets: connection strings never in code — flag this regardless of DB type.
