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
    name VARCHAR(160) NOT NULL,
    document VARCHAR(30),
    email VARCHAR(160),
    phone VARCHAR(40),
    birth_date DATE,
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
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
    notes TEXT,
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
    uploaded_by UUID REFERENCES users(id),
    title VARCHAR(180) NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(60),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
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
ON CONFLICT (code) DO NOTHING;
