#!/bin/sh
set -eu

: "${POSTGRES_READONLY_USER:?POSTGRES_READONLY_USER is required}"
: "${POSTGRES_READONLY_PASSWORD:?POSTGRES_READONLY_PASSWORD is required}"

psql --set ON_ERROR_STOP=1 \
--set readonly_user="$POSTGRES_READONLY_USER" \
--set readonly_password="$POSTGRES_READONLY_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'readonly_user',
    :'readonly_password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'readonly_user'
)
\gexec

ALTER ROLE :"readonly_user"
    LOGIN
    NOINHERIT
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    PASSWORD :'readonly_password';

SELECT format(
    'REVOKE %I FROM %I',
    parent.rolname,
    :'readonly_user'
)
FROM pg_auth_members AS membership
JOIN pg_roles AS parent ON parent.oid = membership.roleid
WHERE membership.member = (
    SELECT oid FROM pg_roles WHERE rolname = :'readonly_user'
)
\gexec

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I',
    current_database(),
    :'readonly_user'
)
\gexec

GRANT USAGE ON SCHEMA public TO :"readonly_user";
REVOKE CREATE ON SCHEMA public FROM :"readonly_user";
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM :"readonly_user";
GRANT SELECT ON vw_ipca_12_meses, vw_juro_real, vw_analise_mensal
    TO :"readonly_user";
SQL
