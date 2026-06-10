ALTER TABLE IF EXISTS lawyer_certificates
    ADD COLUMN IF NOT EXISTS certificate_access_mode VARCHAR(40) NOT NULL DEFAULT 'file_a1';

ALTER TABLE IF EXISTS lawyer_certificates
    ADD COLUMN IF NOT EXISTS certificate_provider VARCHAR(80);

ALTER TABLE IF EXISTS lawyer_certificates
    ADD COLUMN IF NOT EXISTS device_identifier VARCHAR(160);

ALTER TABLE IF EXISTS lawyer_certificates
    ADD COLUMN IF NOT EXISTS local_agent_id VARCHAR(160);

ALTER TABLE IF EXISTS lawyer_certificates
    ADD COLUMN IF NOT EXISTS cloud_certificate_ref VARCHAR(220);

ALTER TABLE IF EXISTS lawyer_certificates
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

UPDATE lawyer_certificates
SET certificate_access_mode = CASE
    WHEN UPPER(COALESCE(certificate_type, '')) = 'A3' THEN 'token_a3_local'
    WHEN COALESCE(certificate_file_url, '') <> '' THEN 'file_a1'
    ELSE certificate_access_mode
END
WHERE certificate_access_mode IS NULL OR certificate_access_mode = 'file_a1';
