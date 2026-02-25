-- Initial Schema for Alfred

-- Users table: Managed by Spring Boot
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Jobs table: Written by FastAPI, claimed and executed by alfred-cli workers
CREATE TABLE IF NOT EXISTS jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Input
    prompt          TEXT NOT NULL,
    repo_path       TEXT,                        -- e.g. /repos/my-project
    branch          TEXT,                        -- git branch to work on
    task_payload    JSONB,                       -- { "allowed_tools": [...], ... }

    -- Status
    -- queued | running | done | failed
    status          VARCHAR(50) NOT NULL DEFAULT 'queued',

    -- Worker lease (prevents double-claiming on crash)
    worker_id       TEXT,
    leased_until    TIMESTAMP WITH TIME ZONE,

    -- Output
    result          TEXT,                        -- human-readable summary
    result_patch    TEXT,                        -- unified diff of changes made
    error_message   TEXT,

    -- Timestamps
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at      TIMESTAMP WITH TIME ZONE,
    completed_at    TIMESTAMP WITH TIME ZONE
);

-- Fast queue scan: workers filter by status and check for expired leases
CREATE INDEX IF NOT EXISTS idx_jobs_queue    ON jobs (status, leased_until);
-- History lookup by user
CREATE INDEX IF NOT EXISTS idx_jobs_user_id  ON jobs (user_id);

-- Job log lines: streamed by workers during execution
CREATE TABLE IF NOT EXISTS job_logs (
    id         BIGSERIAL PRIMARY KEY,
    job_id     UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    logged_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level      VARCHAR(10) NOT NULL DEFAULT 'INFO',  -- INFO | WARN | ERROR
    message    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs (job_id, logged_at);
