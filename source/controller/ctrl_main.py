from source.app import app
from source.core.config.config import appConfig
from source.core.system.database import master_database_ping, validate_master_database_config
from source.core.system.utils import NXResult


def _route_catalog() -> list[dict]:
    return [
        {"method": "GET", "path": "/api/v1/health", "purpose": "healthcheck para Railway"},
        {"method": "GET", "path": "/api/v1/ready", "purpose": "valida configuracao e banco"},
        {"method": "GET", "path": "/api/v1/routes", "purpose": "lista rotas base"},
        {"method": "GET", "path": "/api/v1/conventions", "purpose": "padroes da API"},
        {"method": "GET", "path": "/api/v1/environment", "purpose": "diagnostico de ambiente"},
        {"method": "GET", "path": "/api/v1/about", "purpose": "informacoes do projeto"},
        {"method": "GET", "path": "/api/v1/public/companies/<company_code>", "purpose": "perfil publico do escritorio"},
        {"method": "POST", "path": "/api/v1/public/signup", "purpose": "cadastro publico de escritorio e usuario administrador"},
        {"method": "POST", "path": "/api/v1/public/leads", "purpose": "captura publica de lead"},
        {"method": "POST", "path": "/api/v1/public/client-portal/session", "purpose": "acesso publico ao portal do cliente"},
        {"method": "GET", "path": "/api/v1/public/signatures/<token>", "purpose": "consulta publica de assinatura digital"},
        {"method": "POST", "path": "/api/v1/public/signatures/<token>/sign", "purpose": "assinatura publica de documento"},
        {"method": "GET", "path": "/api/v1/catalog", "purpose": "catalogos auxiliares para frontend"},
        {"method": "GET", "path": "/api/v1/me", "purpose": "perfil do usuario autenticado"},
        {"method": "GET/PUT", "path": "/api/v1/company-settings", "purpose": "configuracoes da empresa atual"},
        {"method": "POST", "path": "/api/v1/setup/bootstrap", "purpose": "bootstrap inicial da empresa"},
        {"method": "POST", "path": "/api/v1/auth/login", "purpose": "login do usuario da empresa"},
        {"method": "POST", "path": "/api/v1/auth/refresh", "purpose": "renova token JWT"},
        {"method": "POST", "path": "/api/v1/auth/logout", "purpose": "revoga refresh token"},
        {"method": "GET", "path": "/api/v1/auth/session", "purpose": "valida sessao atual"},
        {"method": "POST", "path": "/api/v1/auth/change-password", "purpose": "troca senha do usuario"},
        {"method": "POST", "path": "/api/v1/auth/request-password-reset", "purpose": "solicita reset de senha"},
        {"method": "POST", "path": "/api/v1/auth/reset-password", "purpose": "confirma reset de senha"},
        {"method": "GET/POST", "path": "/api/v1/users", "purpose": "usuarios do escritorio"},
        {"method": "GET/POST", "path": "/api/v1/roles", "purpose": "perfis de acesso"},
        {"method": "GET", "path": "/api/v1/permissions", "purpose": "catalogo de permissoes"},
        {"method": "GET/POST", "path": "/api/v1/role-permissions", "purpose": "vinculo entre perfis e permissoes"},
        {"method": "GET/POST", "path": "/api/v1/clients", "purpose": "clientes do escritorio"},
        {"method": "GET/POST", "path": "/api/v1/lawyers", "purpose": "advogados e especialidades"},
        {"method": "GET/POST", "path": "/api/v1/cases", "purpose": "processos do escritorio"},
        {"method": "GET/POST", "path": "/api/v1/agenda-items", "purpose": "camada unificada de agenda e tarefas"},
        {"method": "GET/POST", "path": "/api/v1/appointments", "purpose": "agenda e audiencias"},
        {"method": "GET/POST", "path": "/api/v1/appointment-participants", "purpose": "participantes de compromissos"},
        {"method": "GET/POST", "path": "/api/v1/documents", "purpose": "documentos juridicos"},
        {"method": "POST", "path": "/api/v1/documents/upload", "purpose": "envio de arquivo para documento"},
        {"method": "GET/POST/PUT", "path": "/api/v1/documents/<document_id>/ocr", "purpose": "OCR assistido e revisao textual do documento"},
        {"method": "GET/POST", "path": "/api/v1/document-signature-requests", "purpose": "solicitacoes de assinatura digital"},
        {"method": "GET/POST", "path": "/api/v1/document-templates", "purpose": "modelos de documentos"},
        {"method": "POST", "path": "/api/v1/documents/generate", "purpose": "gera documento por template"},
        {"method": "GET/POST", "path": "/api/v1/message-templates", "purpose": "templates de mensagem"},
        {"method": "GET/POST", "path": "/api/v1/messages", "purpose": "fila e historico de mensagens"},
        {"method": "GET/POST", "path": "/api/v1/financial-entries", "purpose": "lancamentos financeiros do escritorio"},
        {"method": "POST", "path": "/api/v1/messages/send-template", "purpose": "gera envio por template"},
        {"method": "GET/POST", "path": "/api/v1/tasks", "purpose": "tarefas e prazos"},
        {"method": "GET/POST", "path": "/api/v1/task-checklist-items", "purpose": "checklist de tarefas"},
        {"method": "GET/POST", "path": "/api/v1/notifications", "purpose": "notificacoes do usuario"},
        {"method": "GET", "path": "/api/v1/audit", "purpose": "auditoria do tenant"},
        {"method": "GET", "path": "/api/v1/reports/summary", "purpose": "resumo operacional"},
        {"method": "GET", "path": "/api/v1/reports/timeline", "purpose": "timeline operacional"},
        {"method": "GET", "path": "/api/v1/reports/bi", "purpose": "indicadores executivos e BI juridico"},
        {"method": "GET", "path": "/api/v1/reports/financial-summary", "purpose": "resumo consolidado do financeiro com filtros"},
        {"method": "GET", "path": "/api/v1/ai/dashboard-insights", "purpose": "insights executivos da operacao do escritorio"},
        {"method": "GET", "path": "/api/v1/ai/communication-insights/<message_id>", "purpose": "insights operacionais e follow-up da comunicacao"},
        {"method": "GET", "path": "/api/v1/ai/case-insights/<case_id>", "purpose": "insights juridicos e proximos passos do processo"},
        {"method": "GET", "path": "/api/v1/ai/client-insights/<client_id>", "purpose": "insights executivos e relacao operacional do cliente"},
        {"method": "GET", "path": "/api/v1/ai/document-insights/<document_id>", "purpose": "insights executivos, OCR e recomendacoes do documento"},
    ]


@app.route("/api/v1/health")
def health():
    r = NXResult()
    r.status = True
    r.message = "Servico ativo"
    r.data = {
        "service": appConfig.apiName,
        "version": appConfig.apiVersion,
    }
    return r.toJSON()


@app.route("/api/v1/ready")
def ready():
    r = master_database_ping()
    if r.status:
        r.message = "Servico pronto para operacao"
    return r.toJSON(), (200 if r.status else 503)


@app.route("/api/v1/routes")
def routes():
    r = NXResult()
    r.status = True
    r.message = "Rotas base carregadas com sucesso"
    r.data = _route_catalog()
    return r.toJSON()


@app.route("/api/v1/conventions")
def conventions():
    r = NXResult()
    r.status = True
    r.message = "Convencoes da API carregadas com sucesso"
    r.data = {
        "response_pattern": "NXResult",
        "auth_pattern": "Bearer <jwt>",
        "database_strategy": "company_id em todas as tabelas operacionais",
        "deploy_target": "Railway",
    }
    return r.toJSON()


@app.route("/api/v1/environment")
def environment():
    validation = validate_master_database_config()
    r = NXResult()
    r.status = True
    r.message = "Diagnostico do ambiente carregado com sucesso"
    r.data = {
        "name": appConfig.apiName,
        "version": appConfig.apiVersion,
        "database": validation,
        "jwt_expires_hours": appConfig.jwtExpiresHours,
        "setup_key_configured": bool(appConfig.setupKey),
    }
    return r.toJSON()


@app.route("/api/v1/about")
def about():
    r = NXResult()
    r.status = True
    r.message = "Informacoes da API carregadas com sucesso"
    r.data = {
        "name": appConfig.apiName,
        "version": appConfig.apiVersion,
        "info": appConfig.apiInfo,
        "modules": [
            "auth",
            "companies",
            "users",
            "roles",
            "permissions",
            "clients",
            "lawyers",
            "cases",
            "agenda_items",
            "appointments",
            "appointment_participants",
            "documents",
            "document_ocr",
            "document_signature_requests",
            "document_templates",
            "message_templates",
            "messages",
            "financial_entries",
            "tasks",
            "task_checklist_items",
            "notifications",
            "audit",
            "ai_dashboard_insights",
            "ai_communication_insights",
            "ai_case_insights",
            "ai_client_insights",
            "ai_document_insights",
        ],
    }
    return r.toJSON()
