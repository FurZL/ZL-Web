#!/usr/bin/env bash
# Encrypted PostgreSQL dump. The optional upload hook receives archive and checksum paths.
set -euo pipefail
umask 077

: "${BACKUP_AGE_RECIPIENT:?Set BACKUP_AGE_RECIPIENT to an age public recipient}"
: "${PGDATABASE:?Set PGDATABASE to the source database}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/furry-zjut}"
REQUIRE_OFFSITE="${REQUIRE_OFFSITE:-0}"
if [[ "$REQUIRE_OFFSITE" != 0 && "$REQUIRE_OFFSITE" != 1 ]]; then
  echo "REQUIRE_OFFSITE must be 0 or 1" >&2; exit 1
fi
if [[ "$REQUIRE_OFFSITE" == 1 && -z "${BACKUP_UPLOAD_HOOK:-}" ]]; then
  echo "An upload hook is required for offsite backups" >&2; exit 1
fi
command -v age >/dev/null
command -v pg_dump >/dev/null
command -v sha256sum >/dev/null
mkdir -p -- "$BACKUP_DIR"
BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd -P)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP="$(mktemp "$BACKUP_DIR/furry-zjut-${STAMP}-XXXXXXXX.age.tmp")"
trap 'rm -f -- "$TMP"' EXIT
ARCHIVE="${TMP%.tmp}"
pg_dump --format=custom --no-owner --no-privileges | age -r "$BACKUP_AGE_RECIPIENT" > "$TMP"
[[ -s "$TMP" ]] || { echo "Empty encrypted backup" >&2; exit 1; }
mv -- "$TMP" "$ARCHIVE"
(cd "$BACKUP_DIR" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256")
if [[ -n "${BACKUP_UPLOAD_HOOK:-}" ]]; then
  "$BACKUP_UPLOAD_HOOK" "$ARCHIVE" "$ARCHIVE.sha256"
  echo "Encrypted backup uploaded: $ARCHIVE"
else
  echo "Encrypted local backup only: $ARCHIVE" >&2
fi
