CREATE TABLE IF NOT EXISTS certificate_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(160) NOT NULL,
    agent_key VARCHAR(160) NOT NULL,
    token_hash VARCHAR(128) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    last_seen_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(company_id, agent_key)
);

CREATE TABLE IF NOT EXISTS certificate_agent_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    lawyer_id UUID REFERENCES lawyers(id),
    certificate_id UUID REFERENCES lawyer_certificates(id),
    connector_id UUID REFERENCES court_connectors(id),
    agent_id UUID REFERENCES certificate_agents(id),
    assigned_agent_key VARCHAR(160),
    job_type VARCHAR(60) NOT NULL DEFAULT 'tribunal_sync',
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    request_payload JSONB DEFAULT '{}'::jsonb,
    response_payload JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    locked_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_certificate_agent_jobs_pending
    ON certificate_agent_jobs(company_id, assigned_agent_key, status, created_at)
    WHERE deleted_at IS NULL;
