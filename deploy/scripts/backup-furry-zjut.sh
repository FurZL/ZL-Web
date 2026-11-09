#!/usr/bin/env bash
# PostgreSQL 逻辑备份：本地 dump（加密/上传 COS 步骤需按实际工具链补齐）
set -euo pipefail
umask 077

BACKUP_DIR="/var/backups/furry-zjut"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

export PGPASSFILE="/root/.pgpass-furry-zjut"

pg_dump \
  --host=127.0.0.1 \
  --username=furry_backup \
  --dbname=furry_zjut \
  --format=custom \
  --file="$BACKUP_DIR/furry_zjut-$STAMP.dump"

# TODO: 使用 age/gpg 加密，并用云厂商 CLI/SDK 上传到独立备份前缀；
#       上传失败应返回非零并触发告警。

find "$BACKUP_DIR" -type f -name 'furry_zjut-*.dump' -mtime +7 -delete