SQL_USER_BY_COMPANY_EMAIL = """
SELECT
    u.id,
    u.company_id,
    u.role_id,
    u.name,
    u.email,
    u.password_hash,
    u.active,
    c.code AS company_code,
    c.name AS company_name,
    r.name AS role_name
FROM users u
JOIN companies c ON c.id = u.company_id
LEFT JOIN roles r ON r.id = u.role_id
WHERE c.code = %s
  AND LOWER(u.email) = LOWER(%s)
  AND u.deleted_at IS NULL
LIMIT 1
"""

SQL_ROLE_PERMISSIONS = """
SELECT p.code
FROM role_permissions rp
JOIN permissions p ON p.id = rp.permission_id
WHERE rp.role_id = %s
  AND p.active = TRUE
"""
