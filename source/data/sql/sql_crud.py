RESOURCE_SELECT = {
    "companies": """
        SELECT c.id, c.code, c.name, c.document, c.email, c.phone, c.logo_url, c.status, c.plan_id, c.created_at, c.updated_at,
               cs.billing_email, cs.timezone, cs.locale, cs.storage_limit_mb, cs.storage_used_mb, cs.settings
        FROM companies c
        LEFT JOIN company_settings cs ON cs.company_id = c.id
        WHERE c.id = %s AND c.deleted_at IS NULL
    """,
    "users": """
        SELECT id, company_id, role_id, name, email, phone, status, active, last_login_at, created_at, updated_at
        FROM users
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "roles": """
        SELECT id, company_id, name, description, is_admin, active, created_at, updated_at
        FROM roles
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
    "permissions": """
        SELECT id, code, name, description, module_name, active, created_at
        FROM permissions
        WHERE active = TRUE
        ORDER BY module_name, code
    """,
    "role_permissions": """
        SELECT rp.id, rp.role_id, rp.permission_id, p.code AS permission_code, p.name AS permission_name, p.module_name, rp.created_at
        FROM role_permissions rp
        JOIN roles r ON r.id = rp.role_id
        JOIN permissions p ON p.id = rp.permission_id
        WHERE r.company_id = %s
        ORDER BY rp.created_at DESC
    """,
    "clients": """
        SELECT id, company_id, name, document, email, phone, birth_date, notes, status, created_at, updated_at
        FROM clients
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "lawyers": """
        SELECT id, company_id, user_id, name, email, phone, oab_number, oab_state, specialties, active, created_at, updated_at
        FROM lawyers
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "cases": """
        SELECT id, company_id, client_id, lawyer_id, case_number, title, area, court, district, court_branch, phase, status, notes, created_at, updated_at
        FROM cases
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "appointments": """
        SELECT id, company_id, client_id, case_id, title, type, mode, start_at, end_at, location, notes, status, created_by, created_at, updated_at
        FROM appointments
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY start_at DESC, created_at DESC
    """,
    "documents": """
        SELECT id, company_id, client_id, case_id, uploaded_by, title, file_url, file_type, status, created_at, updated_at
        FROM documents
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "tasks": """
        SELECT id, company_id, client_id, case_id, assigned_user_id, title, description, priority, due_at, status, created_by, created_at, updated_at
        FROM tasks
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY due_at NULLS LAST, created_at DESC
    """,
    "message_templates": """
        SELECT id, company_id, name, channel, subject, body, active, created_at, updated_at
        FROM message_templates
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
    "document_templates": """
        SELECT id, company_id, name, category, file_type, template_body, variables, active, created_at, updated_at
        FROM document_templates
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "messages": """
        SELECT id, company_id, client_id, case_id, template_id, channel, recipient, subject, body, status, sent_at, created_by, created_at, updated_at
        FROM messages
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
    "notifications": """
        SELECT id, company_id, user_id, title, body, channel, scheduled_at, sent_at, read_at, attempts, status, created_at, updated_at
        FROM notifications
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
    "appointment_participants": """
        SELECT ap.id, ap.appointment_id, ap.user_id, ap.lawyer_id, ap.participant_name, ap.participant_type, ap.created_at
        FROM appointment_participants ap
        JOIN appointments a ON a.id = ap.appointment_id
        WHERE a.company_id = %s AND a.deleted_at IS NULL
        ORDER BY ap.created_at DESC
    """,
    "task_checklist_items": """
        SELECT tci.id, tci.task_id, tci.title, tci.done, tci.created_at, tci.updated_at
        FROM task_checklist_items tci
        JOIN tasks t ON t.id = tci.task_id
        WHERE t.company_id = %s AND t.deleted_at IS NULL
        ORDER BY tci.created_at DESC
    """,
    "audit_logs": """
        SELECT id, company_id, user_id, entity, entity_id, action, old_data, new_data, created_at
        FROM audit_logs
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
}
