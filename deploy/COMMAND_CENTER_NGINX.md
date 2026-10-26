# Request for the Command Center owner: one line in the nginx config

**Repository:** `it-dev-cast/PULSE-Endpoint-Agent`
**File:** `deploy/commandcenter/nginx-commandcenter.conf` (installed as `/etc/nginx/sites-available/commandcenter` on nexusone-dev-app-01)

Signature Studio is published at `http://192.168.0.190/signature/`. Requests to the server IP are
answered by the Command Center site, so the live file on the server contains one extra line. Please
add the same line to the repository copy, so that re-installing the file from the repo keeps
`/signature` working:

```diff
 server {
+    include /etc/nginx/snippets/signature-studio*.conf;
     listen 80;
     listen [::]:80;
     server_name commandcenter.casterly.com;
```

## Why this is safe for Command Center

- **Wildcard include.** nginx treats a wildcard that matches no file as "nothing to include". If
  Signature Studio is ever removed from the server, this line does nothing and `nginx -t` still passes.
- **Only `/signature` paths.** The snippet (`/etc/nginx/snippets/signature-studio.conf`) defines just
  `location = /signature` and `location ^~ /signature/`, proxied to `127.0.0.1:8280`. It doesn't
  match `/`, `/casterlycommandcenter/`, `/v1/` or the WebSocket path.
- **Nothing else changes.** No `listen`, `server_name`, `root`, headers or other locations are
  added or changed.

## If the line is ever lost

`/signature` returns 404 and Command Center is unaffected. Restore it with:

```bash
sudo bash /opt/signature-studio/app/deploy/enable-nginx.sh
```

The script backs up the site file, adds only this line, runs `nginx -t`, and restores the backup
automatically if the test fails.
