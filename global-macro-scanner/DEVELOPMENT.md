Development

This document describes how to work on this codebase, with a focus on keeping most data logic inside PostgreSQL and using Python as a thin integration layer.
Tech stack

    Language: Python (primary)

    Database: PostgreSQL

    DB access: A small set of centralized Python modules (e.g. db/session.py, db/api.py)

    Migrations: Your preferred tool (e.g. Alembic, Django migrations, or raw SQL files)

The core rule: application logic that is fundamentally about data transformation or querying should live in SQL/PLpgSQL rather than in ad‑hoc Python scripts.
Project layout

Adjust paths to match your repo, but the intended structure is:

    db/

        session.py – connection handling and low‑level helpers

        api.py – functions that wrap SQL queries or stored procedures

    sql/

        functions/ – *.sql files defining Postgres functions and procedures

        views/ – *.sql files defining views and materialized views

    migrations/ – schema and data migrations

    tools/

        db_debug.py – optional single entrypoint for DB debugging utilities

    app/ or similar – rest of the Python application

All new database interactions should go through db/api.py (or an equivalent module documented here).
Database access guidelines

    Single abstraction layer

        All direct database access from Python must go through the DB layer:

            db/session.py handles:

                Creating connections

                Managing transactions

                Returning cursors or high‑level query helpers

            db/api.py exposes:

                Small, well‑named functions that represent operations, e.g.

                    get_user(user_id)

                    recompute_metrics(user_id)

                    backfill_orders(since)

    Where logic lives

        Use SQL or PL/pgSQL for:

            Multi‑step data transformations

            Complex joins and aggregations

            Backfills and maintenance tasks

            Any logic that primarily manipulates data in Postgres

        Use Python for:

            Orchestrating calls to functions/procedures

            Handling HTTP requests, CLI arguments, and background jobs

            Integrating with external services (queues, APIs, storage)

    Preferred pattern

        In SQL (in sql/functions/ or a migration):

        sql
        CREATE OR REPLACE FUNCTION analytics.recompute_metrics(user_id uuid)
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
          -- complex SQL logic here
        END;
        $$;

        In Python (db/api.py):

        python
        from .session import get_connection

        def recompute_metrics(user_id):
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT analytics.recompute_metrics(%s)",
                    (user_id,),
                )

        In application code:

        python
        from db.api import recompute_metrics

        def handle_user_update(user_id):
            recompute_metrics(user_id)

    The goal is that application code never needs to know the SQL details.

Rules for adding or changing code
When you need new DB behavior

    Ask: “Is this primarily data logic?”

        If yes:

            Add or modify a Postgres function/procedure or a view.

            Add a thin wrapper in db/api.py.

        If no (e.g. heavy external I/O or business rules involving multiple systems):

            Implement logic in Python, but still keep DB interactions going through db/api.py.

    Steps to implement:

        Add/modify SQL in:

            sql/functions/*.sql or

            migrations/ (if it must be part of schema evolution)

        Expose a Python wrapper in db/api.py.

        Call that wrapper from the rest of the app.

    Do not:

        Create new standalone Python scripts for one‑off DB operations.

        Add scattered raw SQL calls throughout the codebase.

        Duplicate queries in multiple places.

Creating or modifying migrations

    Schema changes (tables, indexes, constraints) always go through migrations.

    Function/procedure/view changes can be:

        In migrations (for versioned deployment), or

        In dedicated sql/functions/*.sql and sql/views/*.sql files that are applied by your migration tool or startup logic.

    Keep migrations idempotent and backward‑compatible where possible.

Debugging and ad‑hoc operations

To avoid “debug script sprawl”:

    Use one of the following:

        A database client (psql, GUI) for pure SQL experimentation.

        A single Python entrypoint, tools/db_debug.py, for:

            Calling existing functions/procedures with different parameters.

            Running small one‑off maintenance tasks that still use db/api.py.

Rules:

    Do not create new debug scripts under random paths.

    Extend tools/db_debug.py with new subcommands instead.

    If you discover useful logic during debugging:

        Move it into SQL/PLpgSQL and/or db/api.py.

        Keep db_debug.py as a caller, not a place for core logic.

Python coding conventions for DB access

    Use a consistent DB driver (e.g. psycopg/psycopg2, SQLAlchemy core, etc.).

    Centralize connection parameters (host, port, user, password, dbname) in configuration, not scattered literals.

    Always:

        Use context managers (with get_connection() as conn) to ensure connections are closed.

        Handle transactions explicitly (commit/rollback) in the DB layer, not at random call sites.

    Keep DB API functions small:

        One function should generally correspond to a single SQL statement or a single function/procedure call.

        Return plain Python types or simple dataclasses, not raw cursor objects.

How to add a new feature that uses the database

When implementing a new feature:

    Design what the DB operation should be:

        Inputs (parameters)

        Outputs (rows, status, nothing)

    Add a SQL function/procedure/view if needed.

    Add a wrapper in db/api.py with:

        A descriptive name

        A clear signature

    Call that wrapper from your service/handler/task code.

    If the feature needs manual triggering or debugging:

        Add a subcommand to tools/db_debug.py that uses the same API function.

Example:

    Feature: “Rebuild metrics for all users updated in the last day”

        SQL: analytics.rebuild_recent_metrics(since timestamp)

        Python wrapper: db.api.rebuild_recent_metrics(since: datetime)

        CLI: python tools/db_debug.py rebuild_recent_metrics --since 2026-01-19T00:00:00

Testing

    Unit tests:

        Prefer to test Python wrappers (db/api.py) with a test database.

        Avoid mocking SQL unless absolutely necessary; integration‑style tests give more confidence.

    Database tests:

        Use migrations or fixtures to prepare schema and seed data.

        Call SQL functions/procedures either directly (via SQL) or through their Python wrappers.

Summary of expectations

    Most data logic: inside PostgreSQL (functions, procedures, views).

    Python: thin layer for calling DB logic, orchestrating flows, and integrating external systems.

    Database access: centralized in db/session.py and db/api.py.

    Debugging: at most one Python debug entrypoint; no proliferation of tiny throwaway scripts.
