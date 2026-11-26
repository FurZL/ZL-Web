#!/usr/bin/env bash
# Restore into a pre-created, empty, explicitly named verification database only.
set -euo pipefail
umask 077

ARCHIVE="${1:?Usage: verify-backup-furry-zjut.sh encrypted-archive.age}"
: "${BACKUP_AGE_IDENTITY:?Set BACKUP_AGE_IDENTITY to an age identity file}"
: "${VERIFY_DATABASE:?Set VERIFY_DATABASE to an empty furry_restore_check_* database}"
if [[ ! "$VERIFY_DATABASE" =~ ^furry_restore_check_[a-z0-9_]+$ ]]; then
  echo "Refusing database name: use furry_restore_check_*" >&2; exit 1
fi
if [[ "$VERIFY_DATABASE" == "${PGDATABASE:-}" ]]; then
  echo "Refusing to restore into the source database" >&2; exit 1
fi
command -v age >/dev/null
command -v pg_restore >/dev/null
command -v psql >/dev/null
command -v sha256sum >/dev/null
[[ -f "$ARCHIVE" && -f "$ARCHIVE.sha256" ]] || { echo "Archive or checksum missing" >&2; exit 1; }
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256")
count="$(psql -X -A -t -v ON_ERROR_STOP=1 -d "$VERIFY_DATABASE" -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','S','f');")"
if [[ "$count" != 0 ]]; then
  echo "Verification database is not empty; refusing to restore" >&2; exit 1
fi
age -d -i "$BACKUP_AGE_IDENTITY" "$ARCHIVE" | pg_restore --exit-on-error --no-owner --no-privileges -d "$VERIFY_DATABASE"
psql -X -v ON_ERROR_STOP=1 -d "$VERIFY_DATABASE" -c 'SELECT count(*) AS restored_tables FROM information_schema.tables WHERE table_schema = '\''public'\'' AND table_type = '\''BASE TABLE'\'';'
echo "Restore completed in isolated verification database: $VERIFY_DATABASE"
