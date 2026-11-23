-- Read-only database user for Claude (PostgreSQL). Run as a superuser or as the owner of the database objects.
-- Replace: app_db (database), app_schema (an extra schema, if any), app_owner (the role that creates tables), XXXXX (password).
-- Keep the password out of the repository: store it in the developer's .pgpass (or PGPASSFILE), not in CLAUDE.md or settings.

CREATE ROLE claude_ro LOGIN PASSWORD 'XXXXX';

-- The real protection: every transaction of this role is read-only, even if a privilege is granted by mistake later.
ALTER ROLE claude_ro SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE app_db TO claude_ro;
GRANT USAGE ON SCHEMA public, app_schema TO claude_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public, app_schema TO claude_ro;

-- Tables created later: default privileges apply only to objects created by the role named in FOR ROLE
-- (without FOR ROLE: only to objects created by the role running this statement).
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public GRANT SELECT ON TABLES TO claude_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app_schema GRANT SELECT ON TABLES TO claude_ro;

-- Optional, for "which statements write to this table" diagnostics (needs the pg_stat_statements extension):
-- GRANT pg_read_all_stats TO claude_ro;

-- Check (as claude_ro): must fail with "cannot execute ... in a read-only transaction"
--   CREATE TEMP TABLE t (x int);
