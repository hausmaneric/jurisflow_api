CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    description TEXT,
    max_users INTEGER NOT NULL DEFAULT 5,
    max_cases INTEGER NOT NULL DEFAULT 100,
    max_storage_mb INTEGER NOT NULL DEFAULT 1024,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(60) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    document VARCHAR(30),
    email VARCHAR(160),
    phone VARCHAR(40),
    logo_url TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    plan_id UUID REFERENCES plans(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    role_id UUID REFERENCES roles(id),
    name VARCHAR(160) NOT NULL,
    email VARCHAR(160) NOT NULL,
    password_hash TEXT NOT NULL,
    phone VARCHAR(40),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(company_id, email)
);

CREATE TABLE IF NOT EXISTS company_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
    billing_email VARCHAR(160),
    timezone VARCHAR(80) DEFAULT 'America/Sao_Paulo',
    locale VARCHAR(20) DEFAULT 'pt-BR',
    storage_limit_mb INTEGER DEFAULT 1024,
    storage_used_mb INTEGER DEFAULT 0,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS company_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    plan_id UUID REFERENCES plans(id),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    billing_cycle VARCHAR(30) DEFAULT 'monthly',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    billing_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(120) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    description TEXT,
    module_name VARCHAR(80),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    type VARCHAR(30) NOT NULL DEFAULT 'person',
    name VARCHAR(160) NOT NULL,
    document VARCHAR(30),
    rg_ie VARCHAR(40),
    email VARCHAR(160),
    phone VARCHAR(40),
    civil_status VARCHAR(80),
    profession VARCHAR(120),
    birth_date DATE,
    responsible_user_id UUID REFERENCES users(id),
    origin VARCHAR(80),
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS client_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    type VARCHAR(40) NOT NULL DEFAULT 'phone',
    label VARCHAR(80),
    value VARCHAR(180) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS client_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    type VARCHAR(40) NOT NULL DEFAULT 'main',
    street TEXT,
    number VARCHAR(40),
    complement VARCHAR(120),
    district VARCHAR(120),
    city VARCHAR(120),
    state VARCHAR(20),
    postal_code VARCHAR(30),
    country VARCHAR(80) DEFAULT 'Brasil',
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS lawyers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    name VARCHAR(160) NOT NULL,
    email VARCHAR(160),
    phone VARCHAR(40),
    oab_number VARCHAR(40),
    oab_state VARCHAR(10),
    specialties TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS lawyer_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    lawyer_id UUID NOT NULL REFERENCES lawyers(id) ON DELETE CASCADE,
    certificate_name VARCHAR(160) NOT NULL,
    certificate_file_url TEXT,
    certificate_password_secret TEXT,
    certificate_type VARCHAR(30) DEFAULT 'A1',
    issuer VARCHAR(160),
    valid_from DATE,
    valid_until DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    consent_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    consent_text TEXT,
    last_validated_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    lawyer_id UUID REFERENCES users(id),
    case_number VARCHAR(80),
    title VARCHAR(180) NOT NULL,
    area VARCHAR(80),
    court VARCHAR(160),
    district VARCHAR(120),
    court_branch VARCHAR(120),
    phase VARCHAR(80),
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    claim_value NUMERIC(14,2) NOT NULL DEFAULT 0,
    expected_fees NUMERIC(14,2) NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS case_parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id),
    party_type VARCHAR(60) NOT NULL DEFAULT 'other',
    name VARCHAR(180) NOT NULL,
    document VARCHAR(40),
    email VARCHAR(160),
    phone VARCHAR(40),
    role_description VARCHAR(180),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS court_connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    court_code VARCHAR(40) NOT NULL,
    court_name VARCHAR(160) NOT NULL,
    court_system VARCHAR(60) NOT NULL,
    base_url TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'planned',
    supports_public_lookup BOOLEAN NOT NULL DEFAULT TRUE,
    supports_certificate BOOLEAN NOT NULL DEFAULT FALSE,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS case_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    lawyer_id UUID REFERENCES lawyers(id),
    source VARCHAR(40) NOT NULL DEFAULT 'datajud',
    court_system VARCHAR(80),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    documents_found INTEGER NOT NULL DEFAULT 0,
    documents_downloaded INTEGER NOT NULL DEFAULT 0,
    movements_imported INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    raw_data JSONB DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS case_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    source VARCHAR(40) NOT NULL DEFAULT 'manual',
    movement_code VARCHAR(80),
    movement_date TIMESTAMPTZ,
    title VARCHAR(220) NOT NULL,
    description TEXT,
    raw_data JSONB DEFAULT '{}'::jsonb,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS case_documents_synced (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    sync_log_id UUID REFERENCES case_sync_logs(id),
    title VARCHAR(220) NOT NULL,
    source VARCHAR(60) NOT NULL DEFAULT 'tribunal',
    file_url TEXT,
    file_type VARCHAR(60),
    external_id VARCHAR(160),
    status VARCHAR(30) NOT NULL DEFAULT 'available',
    raw_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(160) NOT NULL,
    trigger_type VARCHAR(80) NOT NULL,
    conditions JSONB DEFAULT '{}'::jsonb,
    actions JSONB DEFAULT '[]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ai_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    entity VARCHAR(80) NOT NULL,
    entity_id UUID,
    summary_type VARCHAR(80) NOT NULL DEFAULT 'general',
    summary TEXT NOT NULL,
    next_steps JSONB DEFAULT '[]'::jsonb,
    risks JSONB DEFAULT '[]'::jsonb,
    source_data JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    title VARCHAR(180) NOT NULL,
    type VARCHAR(40) NOT NULL,
    mode VARCHAR(40),
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ,
    location TEXT,
    meeting_url TEXT,
    reminder_minutes INTEGER NOT NULL DEFAULT 15,
    recurrence_rule TEXT,
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'scheduled',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS appointment_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    lawyer_id UUID REFERENCES lawyers(id),
    participant_name VARCHAR(160),
    participant_type VARCHAR(40) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    category_id UUID,
    uploaded_by UUID REFERENCES users(id),
    title VARCHAR(180) NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(60),
    mime_type VARCHAR(120),
    size_bytes BIGINT,
    version_label VARCHAR(60) NOT NULL DEFAULT 'v1',
    origin VARCHAR(80) NOT NULL DEFAULT 'manual',
    expires_at DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS document_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(120),
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    version_label VARCHAR(60) NOT NULL DEFAULT 'v1',
    title VARCHAR(180),
    file_url TEXT NOT NULL,
    file_type VARCHAR(60),
    notes TEXT,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS document_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    uploaded_by UUID REFERENCES users(id),
    title VARCHAR(180) NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(60),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS document_signature_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    requester_user_id UUID REFERENCES users(id),
    signer_name VARCHAR(160) NOT NULL,
    signer_email VARCHAR(160),
    signer_document VARCHAR(40),
    signer_role VARCHAR(80),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    access_token UUID NOT NULL DEFAULT gen_random_uuid(),
    sent_at TIMESTAMPTZ,
    viewed_at TIMESTAMPTZ,
    signed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS document_ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    requested_by UUID REFERENCES users(id),
    status VARCHAR(30) NOT NULL DEFAULT 'processed',
    engine VARCHAR(60) NOT NULL DEFAULT 'jurisflow-assisted-ocr',
    source_file_url TEXT,
    extracted_text TEXT,
    reviewed_text TEXT,
    confidence_score NUMERIC(5,2),
    extracted_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    appointment_id UUID REFERENCES appointments(id),
    assigned_user_id UUID REFERENCES users(id),
    title VARCHAR(180) NOT NULL,
    description TEXT,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    due_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS task_checklist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS message_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(120) NOT NULL,
    channel VARCHAR(40) NOT NULL DEFAULT 'whatsapp',
    situation VARCHAR(120),
    subject VARCHAR(180),
    body TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL DEFAULT 'general',
    file_type VARCHAR(20) NOT NULL DEFAULT 'html',
    template_body TEXT NOT NULL,
    variables JSONB DEFAULT '[]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS generated_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    template_id UUID REFERENCES document_templates(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    document_id UUID REFERENCES documents(id),
    title VARCHAR(180) NOT NULL,
    output_format VARCHAR(20) NOT NULL DEFAULT 'pdf',
    file_url TEXT,
    context JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'generated',
    generated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    template_id UUID REFERENCES message_templates(id),
    channel VARCHAR(40) NOT NULL DEFAULT 'whatsapp',
    recipient VARCHAR(160) NOT NULL,
    subject VARCHAR(180),
    body TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'queued',
    scheduled_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    provider VARCHAR(80),
    provider_message_id VARCHAR(180),
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    created_by UUID REFERENCES users(id),
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    description VARCHAR(180) NOT NULL,
    entry_type VARCHAR(20) NOT NULL DEFAULT 'income',
    category VARCHAR(80) NOT NULL DEFAULT 'general',
    account_label VARCHAR(120),
    amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS message_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    uploaded_by UUID REFERENCES users(id),
    title VARCHAR(180) NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(60),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    title VARCHAR(180) NOT NULL,
    body TEXT NOT NULL,
    channel VARCHAR(40) NOT NULL DEFAULT 'system',
    scheduled_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(160) NOT NULL,
    target_url TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '[]'::jsonb,
    secret TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_status VARCHAR(40),
    last_called_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_name VARCHAR(120) NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    response_code INTEGER,
    response_body TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS api_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(160) NOT NULL,
    token_hash TEXT NOT NULL,
    scopes JSONB DEFAULT '[]'::jsonb,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    appointment_id UUID REFERENCES appointments(id),
    task_id UUID REFERENCES tasks(id),
    document_id UUID REFERENCES documents(id),
    title VARCHAR(180) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(60) NOT NULL DEFAULT 'general',
    visibility VARCHAR(40) NOT NULL DEFAULT 'internal',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    case_id UUID REFERENCES cases(id),
    appointment_id UUID REFERENCES appointments(id),
    title VARCHAR(180) NOT NULL,
    source VARCHAR(40) NOT NULL DEFAULT 'web',
    transcription_type VARCHAR(60) NOT NULL DEFAULT 'meeting',
    status VARCHAR(40) NOT NULL DEFAULT 'draft',
    language VARCHAR(20) NOT NULL DEFAULT 'pt-BR',
    quality_score NUMERIC(5,2),
    consent_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    confidentiality VARCHAR(40) NOT NULL DEFAULT 'internal',
    created_by UUID REFERENCES users(id),
    finalized_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS transcription_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    file_type VARCHAR(80),
    duration_seconds INTEGER,
    status VARCHAR(40) NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS transcription_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    speaker_label VARCHAR(80),
    start_seconds NUMERIC(12,3),
    end_seconds NUMERIC(12,3),
    text TEXT NOT NULL,
    confidence_score NUMERIC(5,2),
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS transcription_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    segment_id UUID REFERENCES transcription_segments(id),
    original_text TEXT,
    reviewed_text TEXT NOT NULL,
    reviewed_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transcription_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    key_points JSONB DEFAULT '[]'::jsonb,
    next_steps JSONB DEFAULT '[]'::jsonb,
    risks JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS transcription_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    entity VARCHAR(120) NOT NULL,
    entity_id UUID,
    action VARCHAR(40) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE clients ADD COLUMN IF NOT EXISTS type VARCHAR(30) NOT NULL DEFAULT 'person';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS rg_ie VARCHAR(40);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS civil_status VARCHAR(80);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS profession VARCHAR(120);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS responsible_user_id UUID REFERENCES users(id);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS origin VARCHAR(80);

ALTER TABLE cases ADD COLUMN IF NOT EXISTS claim_value NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS expected_fees NUMERIC(14,2) NOT NULL DEFAULT 0;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS meeting_url TEXT;
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reminder_minutes INTEGER NOT NULL DEFAULT 15;
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS recurrence_rule TEXT;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES document_categories(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type VARCHAR(120);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS size_bytes BIGINT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_label VARCHAR(60) NOT NULL DEFAULT 'v1';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS origin VARCHAR(80) NOT NULL DEFAULT 'manual';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS expires_at DATE;

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS appointment_id UUID REFERENCES appointments(id);

ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS situation VARCHAR(120);

ALTER TABLE messages ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS provider VARCHAR(80);
ALTER TABLE messages ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR(180);
ALTER TABLE messages ADD COLUMN IF NOT EXISTS error_message TEXT;

INSERT INTO permissions (code, name, description, module_name)
VALUES
    ('companies.read', 'Consultar empresa', 'Permite visualizar dados da empresa', 'companies'),
    ('companies.write', 'Gerenciar empresa', 'Permite editar empresa e configuracoes', 'companies'),
    ('users.read', 'Consultar usuarios', 'Permite visualizar usuarios', 'users'),
    ('users.write', 'Gerenciar usuarios', 'Permite criar e editar usuarios', 'users'),
    ('clients.read', 'Consultar clientes', 'Permite visualizar clientes', 'clients'),
    ('clients.write', 'Gerenciar clientes', 'Permite criar e editar clientes', 'clients'),
    ('lawyers.read', 'Consultar advogados', 'Permite visualizar advogados', 'lawyers'),
    ('lawyers.write', 'Gerenciar advogados', 'Permite criar e editar advogados', 'lawyers'),
    ('cases.read', 'Consultar processos', 'Permite visualizar processos', 'cases'),
    ('cases.write', 'Gerenciar processos', 'Permite criar e editar processos', 'cases'),
    ('appointments.read', 'Consultar agenda', 'Permite visualizar compromissos', 'appointments'),
    ('appointments.write', 'Gerenciar agenda', 'Permite criar e editar compromissos', 'appointments'),
    ('documents.read', 'Consultar documentos', 'Permite visualizar documentos', 'documents'),
    ('documents.write', 'Gerenciar documentos', 'Permite criar e editar documentos', 'documents'),
    ('document_templates.read', 'Consultar modelos de documento', 'Permite visualizar modelos', 'document_templates'),
    ('document_templates.write', 'Gerenciar modelos de documento', 'Permite criar e editar modelos', 'document_templates'),
    ('message_templates.read', 'Consultar templates de mensagem', 'Permite visualizar templates', 'message_templates'),
    ('message_templates.write', 'Gerenciar templates de mensagem', 'Permite criar e editar templates', 'message_templates'),
    ('messages.read', 'Consultar mensagens', 'Permite visualizar mensagens', 'messages'),
    ('messages.write', 'Gerenciar mensagens', 'Permite criar e enviar mensagens', 'messages'),
    ('financial.read', 'Consultar financeiro', 'Permite visualizar lancamentos financeiros', 'financial'),
    ('financial.write', 'Gerenciar financeiro', 'Permite criar e editar lancamentos financeiros', 'financial'),
    ('tasks.read', 'Consultar tarefas', 'Permite visualizar tarefas', 'tasks'),
    ('tasks.write', 'Gerenciar tarefas', 'Permite criar e editar tarefas', 'tasks'),
    ('notifications.read', 'Consultar notificacoes', 'Permite visualizar notificacoes', 'notifications'),
    ('notifications.write', 'Gerenciar notificacoes', 'Permite criar e editar notificacoes', 'notifications'),
    ('reports.read', 'Consultar relatorios', 'Permite visualizar relatorios', 'reports'),
    ('audit.read', 'Consultar auditoria', 'Permite visualizar auditoria', 'audit')
    ,('subscriptions.read', 'Consultar assinaturas', 'Permite visualizar planos e assinaturas', 'subscriptions')
    ,('subscriptions.write', 'Gerenciar assinaturas', 'Permite editar planos e assinaturas', 'subscriptions')
    ,('integrations.read', 'Consultar integracoes', 'Permite visualizar webhooks, tokens e conectores', 'integrations')
    ,('integrations.write', 'Gerenciar integracoes', 'Permite criar webhooks, tokens e conectores', 'integrations')
    ,('sync.read', 'Consultar sincronizacoes', 'Permite visualizar DataJud, tribunal e logs', 'sync')
    ,('sync.write', 'Executar sincronizacoes', 'Permite solicitar sincronizacoes processuais', 'sync')
    ,('notes.read', 'Consultar anotacoes', 'Permite visualizar anotacoes e transcricoes', 'notes')
    ,('notes.write', 'Gerenciar anotacoes', 'Permite criar e editar anotacoes e transcricoes', 'notes')
    ,('ai.read', 'Consultar IA', 'Permite visualizar resumos e insights de IA', 'ai')
    ,('ai.write', 'Gerenciar IA', 'Permite criar resumos e automacoes assistidas', 'ai')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.is_admin = TRUE
ON CONFLICT DO NOTHING;
