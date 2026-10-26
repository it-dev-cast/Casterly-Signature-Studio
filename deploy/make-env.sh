#!/usr/bin/env bash
# Creates /opt/signature-studio/.env (mode 600) with freshly generated secrets.
# Usage:  bash make-env.sh [public-url]      (default http://192.168.0.190/signature)
# Refuses to overwrite an existing .env: the DB password in it must match the database volume.
set -euo pipefail

ENV_FILE=/opt/signature-studio/.env
PUBLIC_URL="${1:-http://192.168.0.190/signature}"
PUBLIC_URL="${PUBLIC_URL%/}"
ORIGIN=$(printf '%s' "$PUBLIC_URL" | sed -E 's#^(https?://[^/]+).*#\1#')   # scheme://host[:port]
ROOT_PATH="${PUBLIC_URL#"$ORIGIN"}"                                         # e.g. /signature

if [ -e "$ENV_FILE" ]; then
  echo "$ENV_FILE already exists - not overwriting it." >&2
  exit 1
fi

umask 077
DB_PASSWORD=$(openssl rand -hex 24)
APP_SECRET=$(openssl rand -hex 32)

cat > "$ENV_FILE" <<EOF
ENVIRONMENT=production

# PostgreSQL container
POSTGRES_DB=signature_studio
POSTGRES_USER=signature_app
POSTGRES_PASSWORD=${DB_PASSWORD}

# API. The app uses psycopg 3, so the driver is postgresql+psycopg (not psycopg2).
DATABASE_URL=postgresql+psycopg://signature_app:${DB_PASSWORD}@postgres:5432/signature_studio
SECRET_KEY=${APP_SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=60
REMEMBER_ME_EXPIRE_DAYS=7

# Absolute base (including the /signature sub-path) for every link and image the app generates.
# Email recipients must be able to reach it.
PUBLIC_BASE_URL=${PUBLIC_URL}
# Sub-path the host nginx publishes the app under.
ROOT_PATH=${ROOT_PATH}
# Browser origins, without any path. Comma-separated list (not JSON).
CORS_ORIGINS=${ORIGIN}

UPLOAD_DIR=uploads
MAX_UPLOAD_MB=5

# Outgoing email for "Send email". Leave SMTP_HOST empty to disable.
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_SECURITY=starttls

# nexusAuth employee sync (optional). Leave NEXUSAUTH_URL empty to disable.
NEXUSAUTH_URL=
NEXUSAUTH_EMAIL=
NEXUSAUTH_PASSWORD=
NEXUSAUTH_SYNC_SECONDS=30
EOF

unset DB_PASSWORD APP_SECRET
chmod 600 "$ENV_FILE"
ls -l "$ENV_FILE"
