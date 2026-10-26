# Signature Studio — Ubuntu deployment (192.168.0.190)

This follows the same phases as the *Nexus Core Ubuntu Deployment Runbook*, with the values and
commands corrected for Signature Studio. Where this file and the Nexus Core runbook differ, use this file.

| Setting | Value |
|---|---|
| Server | `192.168.0.190`, SSH user `nexusone` |
| Deployment root | `/opt/signature-studio` |
| Source | `/opt/signature-studio/app` (contains `backend/` and `frontend/`) |
| Compose file | `/opt/signature-studio/compose.yaml` (from `deploy/compose.yaml`) |
| Environment | `/opt/signature-studio/.env`, mode 600 (made by `deploy/make-env.sh`) |
| Database | `signature_studio`, user `signature_app`, container `signature-studio-postgres` (private network only) |
| API | container `signature-studio-api`, `127.0.0.1:8200` |
| Frontend | container `signature-studio-frontend`, `127.0.0.1:8280` |
| Public URL | `http://192.168.0.190` (host nginx, port 80) |

### What differs from the Nexus Core runbook (these would otherwise fail)

| Nexus Core runbook | Signature Studio | Why |
|---|---|---|
| `api/` folder | `backend/` | Different project layout |
| `postgresql+psycopg2://` | `postgresql+psycopg://` | Only psycopg 3 is installed. psycopg2 → `ModuleNotFoundError` |
| `CORS_ORIGINS=["http://…"]` | `CORS_ORIGINS=http://…` | The app reads a comma-separated list, not JSON |
| `/api/v1/health` | `/api/health` | No `/v1` prefix in this API |
| `VITE_API_BASE_URL: /api/v1` build arg | *(none)* | That value would make every call `/api/v1/api/...` |
| service name `api` only | `api` with network alias `backend` | The frontend nginx proxies to `http://backend:8000`. Without the alias it won't start |
| no uploads volume | `uploads` volume | Uploaded photos and banners would be lost on every rebuild |
| — | `PUBLIC_BASE_URL=http://192.168.0.190` | Image links in email signatures are built from it |
| restore a PostgreSQL dump | fresh database (optional SQLite import, Phase I) | Existing data is SQLite, not a PG dump |

The rules from the Nexus Core runbook §1.2 still apply. Never run `docker compose down -v`,
never delete volumes, never publish 5432, and never post `.env` contents anywhere.

---

## Phase A — Connect

Windows PowerShell:

```powershell
ping 192.168.0.190
ssh nexusone@192.168.0.190
```

On Ubuntu:

```bash
whoami; hostname; hostname -I
```

`hostname -I` must include `192.168.0.190`. Write the hostname down for the report.

## Phase B — Pre-deployment audit

```bash
df -h /; free -h; nproc
docker --version && docker compose version
nginx -v; openssl version
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
sudo ss -tlnp | grep -E ':(80|8200|8280) ' || echo "ports 80/8200/8280 free"
ls -ld /opt/signature-studio 2>/dev/null || echo "no existing deployment"
```

- If root disk use is over ~85%, stop.
- If `docker compose` is missing: `sudo apt-get install -y docker-compose-plugin`. If nginx is missing: `sudo apt-get install -y nginx`.
- If **8200/8280** are taken, change them in `compose.yaml` and `nginx-site.conf` before continuing.
- If **port 80** is already used by another site, see Phase M before cutting over.
- If `/opt/signature-studio` exists, inspect it or back it up. Don't overwrite it blindly.

## Phase C — Package the source (Windows)

The local repository has no commits and no GitHub remote yet, so copy the source directly.
When a GitHub repo exists, you can use `git clone` into `/opt/signature-studio/app` instead (runbook Phase C/D).

The package `C:\Users\Dell\projects\signature-studio-src.tgz` is already built. It contains no `.env`,
`node_modules`, `.venv`, database files or uploads. To rebuild it after code changes:

```powershell
cd C:\Users\Dell\projects
tar -czf signature-studio-src.tgz --exclude=node_modules --exclude=.venv --exclude=.git --exclude=dist --exclude=__pycache__ --exclude=.pytest_cache --exclude=*.tsbuildinfo --exclude=*.db --exclude=.env --exclude=signature-studio/backend/uploads/* signature-studio
scp signature-studio-src.tgz nexusone@192.168.0.190:/tmp/
```

## Phase D — Server structure

```bash
sudo mkdir -p /opt/signature-studio/app /opt/signature-studio/backups
sudo chown -R nexusone:nexusone /opt/signature-studio
chmod 750 /opt/signature-studio
tar -xzf /tmp/signature-studio-src.tgz -C /opt/signature-studio/app --strip-components=1
cp /opt/signature-studio/app/deploy/compose.yaml /opt/signature-studio/compose.yaml

cd /opt/signature-studio/app
test -f backend/Dockerfile      && echo "API Dockerfile OK"
test -f backend/requirements.txt && echo "API requirements OK"
test -f backend/alembic.ini     && echo "Alembic config OK"
test -f frontend/Dockerfile     && echo "Frontend Dockerfile OK"
test -f frontend/package.json   && echo "Frontend package OK"
```

All five must print OK.

## Phase E — Secrets / `.env`

```bash
bash /opt/signature-studio/app/deploy/make-env.sh http://192.168.0.190
```

Expected: `-rw------- … /opt/signature-studio/.env`. The script won't overwrite an existing `.env`,
because the database password in it must keep matching the database volume.

Optional settings: SMTP (for "Send email") and nexusAuth sync. Edit them with `nano /opt/signature-studio/.env`.
Never `cat` this file in a shared screen.

## Phase F — Validate compose

```bash
cd /opt/signature-studio
docker compose config --quiet && echo "compose OK"
```

## Phase G — PostgreSQL

```bash
cd /opt/signature-studio
docker compose up -d postgres
docker compose ps                  # signature-studio-postgres ... (healthy)
docker port signature-studio-postgres   # must print nothing
```

## Phase H/I — Data

**Default: fresh database.** Nothing to do. The API creates every table with Alembic when it starts in Phase J.

**Optional: bring the local SQLite data across** (employees, templates, banners, audit log).
Do this *after* Phase J, into the still-empty database. From Windows:

```powershell
cd C:\Users\Dell\projects\signature-studio\backend
tar -czf uploads.tgz -C uploads photos banners
scp signature_studio.db uploads.tgz nexusone@192.168.0.190:/tmp/
```

On Ubuntu:

```bash
cd /opt/signature-studio
docker compose cp /tmp/signature_studio.db api:/tmp/import.db
docker compose exec api python -m app.import_sqlite /tmp/import.db
mkdir -p /tmp/up && tar -xzf /tmp/uploads.tgz -C /tmp/up
docker compose cp /tmp/up/. api:/app/uploads/
docker compose exec -u root api chown -R appuser /app/uploads
rm -rf /tmp/up /tmp/uploads.tgz /tmp/signature_studio.db
```

The importer refuses to write into a database that already has data. The local database's only
login is the development admin `admin@example.com`, whose password is public. **Reset it right after the import:**
`docker compose exec api python -m app.create_admin --email admin@example.com --reset`

## Phase J — Build and start

```bash
cd /opt/signature-studio
docker compose build --pull api frontend
docker compose up -d api frontend
docker compose ps        # all three Up; api and postgres (healthy)
docker compose logs --tail=100 api
docker compose logs --tail=50 frontend
```

The API log should show the Alembic upgrades (first run only) and `Uvicorn running on http://0.0.0.0:8000`.

## Phase K — Migrations

The API container runs `alembic upgrade head` every time it starts. Verify:

```bash
docker compose exec api alembic current
docker compose exec api alembic heads
```

Both must print `0005 (head)`. Before deploying future code that adds migrations, take a backup first:

```bash
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > /opt/signature-studio/backups/before_$(date +%Y%m%d_%H%M%S).dump
```

## Create the first admin login

(Skip this if you imported data and reset `admin@example.com` above.) Never run `app.seed` in production,
because it creates accounts with public passwords.

```bash
docker compose exec api python -m app.create_admin --email you@casterly.com
```

You'll be asked for the password twice (minimum 12 characters). It's never shown or stored in shell history.

## Phase L — Health checks

```bash
curl -i  http://127.0.0.1:8200/api/health          # 200 {"success":true,"data":{"status":"ok"}}
curl -I  http://127.0.0.1:8280                     # 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8280/api/health              # 200 (through frontend nginx)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8280/outlook-addin/manifest.xml  # 200
docker compose ps
```

## Phase M — Publish on port 80 (host nginx)

```bash
sudo mkdir -p /opt/signature-studio/backups/nginx
sudo cp -a /etc/nginx/sites-enabled /opt/signature-studio/backups/nginx/sites-enabled.$(date +%Y%m%d_%H%M%S)
grep -Rn "default_server" /etc/nginx/sites-enabled/ || echo "no other default_server"
ls -l /etc/nginx/sites-enabled/
```

- If the only enabled site is nginx's stock `default`, disable its symlink: `sudo rm /etc/nginx/sites-enabled/default`.
- If **another application** already serves port 80 on this server, **stop and ask the lead**. Taking over port 80 replaces it.

```bash
sudo cp /opt/signature-studio/app/deploy/nginx-site.conf /etc/nginx/sites-available/signature-studio
sudo ln -sfn /etc/nginx/sites-available/signature-studio /etc/nginx/sites-enabled/signature-studio
sudo nginx -t                       # must say "syntax is ok" and "test is successful"
sudo systemctl reload nginx
curl -I http://127.0.0.1
curl -I http://192.168.0.190
```

If `ufw` is active, allow HTTP: `sudo ufw status` → `sudo ufw allow 80/tcp`.

Open **http://192.168.0.190** on your PC and sign in with the admin you created.

## Acceptance checklist

- [ ] `/opt/signature-studio/.env` exists, mode 600
- [ ] `signature-studio-postgres` healthy, `docker port` prints nothing
- [ ] `signature-studio-api` healthy, `/api/health` → 200
- [ ] `signature-studio-frontend` running, `127.0.0.1:8280` → 200
- [ ] `alembic current` = `alembic heads` = `0005 (head)`
- [ ] An admin can sign in at http://192.168.0.190
- [ ] Uploading an employee photo works and the image shows in the signature preview
- [ ] `nginx -t` passed before reload
- [ ] No other container on the server was stopped or changed

## Rollback

```bash
sudo rm -f /etc/nginx/sites-enabled/signature-studio
# restore whatever was in sites-enabled before, from /opt/signature-studio/backups/nginx/
sudo nginx -t && sudo systemctl reload nginx
cd /opt/signature-studio && docker compose stop api frontend     # keep volumes; never use -v
```

## Updating later

```bash
# copy the new source (new tgz, or git pull in /opt/signature-studio/app), then:
cd /opt/signature-studio
docker compose build api frontend
docker compose up -d api frontend
docker compose ps
```

Don't recreate PostgreSQL or touch the volumes for code updates.

## Note on the Outlook add-in

Outlook add-ins only load over **HTTPS** from a public host. The plain `http://192.168.0.190` LAN URL
works for the web app, setup pages and the Windows installer, but not for the Outlook add-in manifest.
Enabling the add-in means putting a permanent HTTPS hostname (a DNS name, or a *named* Cloudflare Tunnel with
its own hostname) in front of port 80 and setting `PUBLIC_BASE_URL` and `CORS_ORIGINS` to that https URL, then
`docker compose up -d api` so the change is applied. Temporary `trycloudflare.com` quick-tunnel addresses are
refused at startup: they change whenever the tunnel restarts, which breaks every setup link already sent.
