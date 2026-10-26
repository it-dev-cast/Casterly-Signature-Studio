#!/usr/bin/env bash
# Publishes Signature Studio at http://<server>/signature/ through the host nginx.
# Run once, as:  sudo bash /opt/signature-studio/app/deploy/enable-nginx.sh
#
# On 192.168.0.190 requests to the server IP are answered by the Command Center site, so the
# /signature location is added to that site with a single `include` line. Nothing else in the
# file changes. The file is backed up first, and if `nginx -t` fails everything is put back.
#
# The include uses a wildcard (signature-studio*.conf). nginx treats a wildcard that matches no
# file as "nothing to include", so deleting Signature Studio's snippet can never make nginx fail
# for the other sites on this server. Re-running this script is safe; it only upgrades an older
# exact-file include line to the wildcard form.
set -euo pipefail

SITE=/etc/nginx/sites-available/commandcenter
SNIPPET=/etc/nginx/snippets/signature-studio.conf
SOURCE=/opt/signature-studio/app/deploy/nginx-signature.conf
BACKUP_DIR=/opt/signature-studio/backups/nginx
PATTERN="/etc/nginx/snippets/signature-studio*.conf"
INCLUDE="    include $PATTERN;"

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo." >&2; exit 1; }
[ -f "$SITE" ] || { echo "$SITE not found - stop and ask the lead." >&2; exit 1; }
[ "$(grep -c '^\s*server\s*{' "$SITE")" -eq 1 ] || { echo "$SITE has more than one server block - stop." >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
cp -a "$SITE" "$BACKUP_DIR/commandcenter.$STAMP"
[ -f "$SNIPPET" ] && cp -a "$SNIPPET" "$BACKUP_DIR/signature-studio.conf.$STAMP"
echo "Backed up $SITE to $BACKUP_DIR/commandcenter.$STAMP"

install -m 644 "$SOURCE" "$SNIPPET"
if grep -qF "include $PATTERN;" "$SITE"; then
  echo "include line already present - site file unchanged"
elif grep -qF "include $SNIPPET;" "$SITE"; then
  # Older exact-file line: switch it to the fail-safe wildcard.
  sed -i "s|include $SNIPPET;|include $PATTERN;|" "$SITE"
  echo "Upgraded include line to the fail-safe wildcard form"
else
  # Add the include right after the opening "server {" line.
  sed -i "0,/^\s*server\s*{/s||&\n$INCLUDE|" "$SITE"
  echo "Added: $INCLUDE"
fi

if nginx -t; then
  systemctl reload nginx
  echo "nginx reloaded."
  sleep 3  # let the old nginx workers finish so the checks below see the new configuration
else
  echo "nginx -t FAILED - restoring the previous configuration." >&2
  cp -a "$BACKUP_DIR/commandcenter.$STAMP" "$SITE"
  if [ -f "$BACKUP_DIR/signature-studio.conf.$STAMP" ]; then cp -a "$BACKUP_DIR/signature-studio.conf.$STAMP" "$SNIPPET"; else rm -f "$SNIPPET"; fi
  nginx -t && echo "Previous configuration restored; nothing changed." >&2
  exit 1
fi

for url in http://127.0.0.1/signature/ http://127.0.0.1/signature/api/health http://127.0.0.1/casterlycommandcenter/; do
  printf '%-45s %s\n' "$url" "$(curl -s -o /dev/null -m 10 -w '%{http_code}' -H 'Host: 192.168.0.190' "$url")"
done
