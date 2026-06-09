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
    "company_subscriptions": """
        SELECT cs.id, cs.company_id, cs.plan_id, p.name AS plan_name, cs.status, cs.billing_cycle,
               cs.current_period_start, cs.current_period_end, cs.cancelled_at, cs.billing_data, cs.created_at, cs.updated_at
        FROM company_subscriptions cs
        LEFT JOIN plans p ON p.id = cs.plan_id
        WHERE cs.company_id = %s AND cs.deleted_at IS NULL
        ORDER BY cs.created_at DESC
    """,
    "clients": """
        SELECT id, company_id, name, document, email, phone, birth_date, notes, status, created_at, updated_at
        FROM clients
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "client_contacts": """
        SELECT id, company_id, client_id, type, label, value, is_primary, notes, created_at, updated_at
        FROM client_contacts
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY is_primary DESC, created_at DESC
    """,
    "client_addresses": """
        SELECT id, company_id, client_id, type, street, number, complement, district, city, state, postal_code,
               country, is_primary, notes, created_at, updated_at
        FROM client_addresses
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY is_primary DESC, created_at DESC
    """,
    "lawyers": """
        SELECT id, company_id, user_id, name, email, phone, oab_number, oab_state, specialties, active, created_at, updated_at
        FROM lawyers
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "lawyer_certificates": """
        SELECT id, company_id, lawyer_id, certificate_name, certificate_file_url, certificate_type, issuer,
               valid_from, valid_until, status, consent_accepted, consent_text, last_validated_at, created_by,
               created_at, updated_at
        FROM lawyer_certificates
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "cases": """
        SELECT id, company_id, client_id, lawyer_id, case_number, title, area, court, district, court_branch, phase, status, notes, created_at, updated_at
        FROM cases
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "case_parties": """
        SELECT id, company_id, case_id, client_id, party_type, name, document, email, phone, role_description,
               notes, created_at, updated_at
        FROM case_parties
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "court_connectors": """
        SELECT id, company_id, court_code, court_name, court_system, base_url, status, supports_public_lookup,
               supports_certificate, settings, created_at, updated_at
        FROM court_connectors
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY court_name ASC
    """,
    "case_sync_logs": """
        SELECT id, company_id, case_id, lawyer_id, source, court_system, status, started_at, finished_at,
               documents_found, documents_downloaded, movements_imported, error_message, raw_data, created_by,
               created_at, updated_at
        FROM case_sync_logs
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "case_movements": """
        SELECT id, company_id, case_id, source, movement_code, movement_date, title, description, raw_data,
               imported_at, created_at, updated_at
        FROM case_movements
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY movement_date DESC NULLS LAST, created_at DESC
    """,
    "case_documents_synced": """
        SELECT id, company_id, case_id, sync_log_id, title, source, file_url, file_type, external_id, status,
               raw_data, created_at, updated_at
        FROM case_documents_synced
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "automation_rules": """
        SELECT id, company_id, name, trigger_type, conditions, actions, active, created_by, created_at, updated_at
        FROM automation_rules
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "ai_summaries": """
        SELECT id, company_id, entity, entity_id, summary_type, summary, next_steps, risks, source_data, status,
               created_by, created_at, updated_at
        FROM ai_summaries
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
    "document_versions": """
        SELECT id, company_id, document_id, created_by, version_label, title, file_url, file_type, notes, is_current, created_at, updated_at
        FROM document_versions
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "document_attachments": """
        SELECT id, company_id, document_id, uploaded_by, title, file_url, file_type, notes, created_at, updated_at
        FROM document_attachments
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "document_signature_requests": """
        SELECT id, company_id, document_id, requester_user_id, signer_name, signer_email, signer_document, signer_role,
               status, access_token, sent_at, viewed_at, signed_at, cancelled_at, notes, created_at, updated_at
        FROM document_signature_requests
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "document_categories": """
        SELECT id, company_id, name, slug, description, active, created_at, updated_at
        FROM document_categories
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY name ASC
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
    "generated_documents": """
        SELECT id, company_id, template_id, client_id, case_id, document_id, title, output_format, file_url,
               context, status, generated_by, created_at, updated_at
        FROM generated_documents
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "messages": """
        SELECT id, company_id, client_id, case_id, template_id, channel, recipient, subject, body, status, sent_at, created_by, created_at, updated_at
        FROM messages
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
    "financial_entries": """
        SELECT fe.id, fe.company_id, fe.client_id, fe.case_id, fe.created_by, fe.entry_date, fe.description,
               fe.entry_type, fe.category, fe.account_label, fe.amount, fe.status, fe.notes,
               fe.created_at, fe.updated_at,
               c.name AS client_name,
               cs.case_number
        FROM financial_entries fe
        LEFT JOIN clients c ON c.id = fe.client_id
        LEFT JOIN cases cs ON cs.id = fe.case_id
        WHERE fe.company_id = %s AND fe.deleted_at IS NULL
        ORDER BY fe.entry_date DESC, fe.created_at DESC
    """,
    "message_attachments": """
        SELECT id, company_id, message_id, uploaded_by, title, file_url, file_type, notes, created_at, updated_at
        FROM message_attachments
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "notifications": """
        SELECT id, company_id, user_id, title, body, channel, scheduled_at, sent_at, read_at, attempts, status, created_at, updated_at
        FROM notifications
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
    "webhooks": """
        SELECT id, company_id, name, target_url, events, active, last_status, last_called_at, created_by,
               created_at, updated_at
        FROM webhooks
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "webhook_deliveries": """
        SELECT id, company_id, webhook_id, event_name, payload, status, response_code, response_body, attempts,
               next_retry_at, delivered_at, created_at, updated_at
        FROM webhook_deliveries
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "api_tokens": """
        SELECT id, company_id, name, scopes, rate_limit_per_minute, status, last_used_at, expires_at, created_by,
               created_at, updated_at
        FROM api_tokens
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "notes": """
        SELECT id, company_id, client_id, case_id, appointment_id, task_id, document_id, title, content, type,
               visibility, created_by, created_at, updated_at
        FROM notes
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "transcriptions": """
        SELECT id, company_id, client_id, case_id, appointment_id, title, source, transcription_type, status,
               language, quality_score, consent_confirmed, confidentiality, created_by, finalized_at, created_at, updated_at
        FROM transcriptions
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "transcription_files": """
        SELECT id, company_id, transcription_id, file_url, file_type, duration_seconds, status, created_at, updated_at
        FROM transcription_files
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "transcription_segments": """
        SELECT id, company_id, transcription_id, speaker_label, start_seconds, end_seconds, text, confidence_score,
               reviewed, created_at, updated_at
        FROM transcription_segments
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY start_seconds NULLS LAST, created_at ASC
    """,
    "transcription_reviews": """
        SELECT id, company_id, transcription_id, segment_id, original_text, reviewed_text, reviewed_by, created_at
        FROM transcription_reviews
        WHERE company_id = %s
        ORDER BY created_at DESC
    """,
    "transcription_summaries": """
        SELECT id, company_id, transcription_id, summary, key_points, next_steps, risks, status, created_by,
               created_at, updated_at
        FROM transcription_summaries
        WHERE company_id = %s AND deleted_at IS NULL
        ORDER BY created_at DESC
    """,
    "transcription_tasks": """
        SELECT tt.id, tt.company_id, tt.transcription_id, tt.task_id, t.title AS task_title, t.status AS task_status, tt.created_at
        FROM transcription_tasks tt
        JOIN tasks t ON t.id = tt.task_id
        WHERE tt.company_id = %s
        ORDER BY tt.created_at DESC
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
