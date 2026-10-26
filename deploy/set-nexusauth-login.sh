#!/usr/bin/env bash
# Sets the nexusAuth account Signature Studio uses to sync employees, then restarts the API.
# Run (no sudo needed):  bash /opt/signature-studio/app/deploy/set-nexusauth-login.sh
#
# The password is typed at a hidden prompt, checked against nexusAuth once, and only then
# written to /opt/signature-studio/.env (mode 600). It is never printed.
set -euo pipefail

cd /opt/signature-studio
ENV_FILE=.env
NEXUS_CHECK_URL=http://127.0.0.1:8300   # nexusAuth as seen from this server

read -r -p "nexusAuth email (an operator or admin account): " NX_EMAIL
read -r -s -p "nexusAuth password (hidden): " NX_PASS; echo
[ -n "$NX_EMAIL" ] && [ -n "$NX_PASS" ] || { echo "Email and password are both required." >&2; exit 1; }

echo "Checking the login with nexusAuth..."
STATUS=$(NX_EMAIL="$NX_EMAIL" NX_PASS="$NX_PASS" python3 - "$NEXUS_CHECK_URL" <<'PY'
import json, os, sys, urllib.request, urllib.error
body = json.dumps({"email": os.environ["NX_EMAIL"], "password": os.environ["NX_PASS"]}).encode()
req = urllib.request.Request(sys.argv[1] + "/api/v1/auth/login", data=body, headers={"Content-Type": "application/json"})
try:
    urllib.request.urlopen(req, timeout=10)
    print("ok")
except urllib.error.HTTPError as e:
    print(e.code)
except Exception as e:
    print("unreachable")
PY
)
case "$STATUS" in
  ok) echo "Login accepted by nexusAuth." ;;
  401|403) echo "nexusAuth rejected that email/password. Nothing was changed. (nexusAuth locks an account after 5 failed tries.)" >&2; exit 1 ;;
  429) echo "nexusAuth is rate-limiting sign-ins. Wait a minute and try again. Nothing was changed." >&2; exit 1 ;;
  *) echo "Could not check the login with nexusAuth ($STATUS). Nothing was changed." >&2; exit 1 ;;
esac

cp -a "$ENV_FILE" "backups/.env.before-nexusauth-login.$(date +%Y%m%d_%H%M%S)"
chmod 600 backups/.env.before-nexusauth-login.*
NX_EMAIL="$NX_EMAIL" NX_PASS="$NX_PASS" python3 - "$ENV_FILE" <<'PY'
import os, sys
path = sys.argv[1]
values = {"NEXUSAUTH_EMAIL": os.environ["NX_EMAIL"], "NEXUSAUTH_PASSWORD": os.environ["NX_PASS"]}
lines, done = [], set()
for line in open(path, encoding="utf-8").read().splitlines():
    key = line.split("=", 1)[0]
    if key in values:
        line = f"{key}={values[key]}"
        done.add(key)
    lines.append(line)
lines += [f"{k}={v}" for k, v in values.items() if k not in done]
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY
chmod 600 "$ENV_FILE"
unset NX_PASS
echo "Saved to $ENV_FILE."

echo "Restarting the Signature Studio API..."
docker compose up -d api >/dev/null
for i in $(seq 1 30); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' signature-studio-api 2>/dev/null)" = healthy ] && break
  sleep 3
done
sleep 5
echo "API: $(docker inspect -f '{{.State.Health.Status}}' signature-studio-api)"
echo "Latest sync messages:"
docker compose logs --since 3m api 2>&1 | grep -i "nexus" | tail -5 || true
echo "Done. Open http://192.168.0.190/signature/admin/employees and look for the nexusAuth sync bar."
