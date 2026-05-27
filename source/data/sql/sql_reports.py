SQL_TIMELINE = """
SELECT 'appointment' AS entity, id, title AS label, start_at AS reference_at, status
FROM appointments
WHERE company_id = %s AND deleted_at IS NULL
UNION ALL
SELECT 'task' AS entity, id, title AS label, due_at AS reference_at, status
FROM tasks
WHERE company_id = %s AND deleted_at IS NULL
UNION ALL
SELECT 'case' AS entity, id, title AS label, updated_at AS reference_at, status
FROM cases
WHERE company_id = %s AND deleted_at IS NULL
ORDER BY reference_at DESC NULLS LAST
LIMIT 50
"""
