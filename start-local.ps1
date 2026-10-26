# Starts the Casterly stack on this PC and publishes Signature Studio to the internet.
# Run it with start-local.cmd (double-click).
#
#   nexusAuth                       http://localhost:8000/ui    employee data
#   Signature Studio admin app      http://localhost:5173       open this one (private, this PC only)
#   Signature Studio admin backend  http://localhost:8001       private, this PC only
#   Public gateway                  http://localhost:8090       ONLY the public routes: setup pages, Outlook add-in
#                                                               files, signatures, banner, images, installer
#
# Public address - two modes:
#   * $permanentUrl EMPTY (default, no accounts needed): a Cloudflare quick tunnel. Its address is random
#     and CHANGES whenever the tunnel restarts (e.g. after a PC restart). This script puts the current one
#     into backend\.env (PUBLIC_BASE_URL); setup links, add-ins and installers made with an older address
#     stop working and must be re-sent.
#   * $permanentUrl SET (e.g. 'https://signatures.casterly.com'): a permanent address that IT set up -
#     a Cloudflare named tunnel installed on this PC with `cloudflared service install <token>`, routing
#     that hostname to http://localhost:8090. Links never change, and the same address can later point at
#     the server, so links sent now keep working after deployment.
# Anything already running is left alone. Close a window to stop that server.

$permanentUrl = ''  # set this when IT provides a permanent hostname

$ErrorActionPreference = 'Stop'
$studio = $PSScriptRoot
$nexusAuth = 'C:\Users\Dell\Desktop\nexusAuth'
$cloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
$envFile = Join-Path $studio 'backend\.env'
$tunnelLog = Join-Path $env:TEMP 'signature-studio-tunnel.log'
$tunnelMetrics = 20241  # the quick tunnel's local metrics port: tells us it is running

function Test-Port([int]$port) {
    [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

function Start-Server([string]$title, [string]$dir, [string]$command) {
    Write-Host "Starting $title..."
    Start-Process cmd.exe -WorkingDirectory $dir -ArgumentList "/k title $title && $command"
}

function Stop-Port([int]$port) {
    foreach ($c in Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        & taskkill.exe /T /F /PID $c.OwningProcess | Out-Null
    }
}

function Wait-Port([int]$port, [int]$seconds = 45) {
    for ($i = 0; $i -lt $seconds; $i++) { if (Test-Port $port) { return $true }; Start-Sleep 1 }
    return $false
}

function Fail([string]$message) {
    Write-Host $message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}

# 0a. Both apps keep their data in PostgreSQL (port 5432). Its Windows service starts with Windows.
if (-not (Test-Port 5432)) {
    Fail ("PostgreSQL is not running on port 5432. Start it in Windows Services (postgresql-x64-18), " +
          "or run as administrator:  Start-Service postgresql-x64-18")
}

# 0. The frontend must proxy to the Signature Studio backend (8001). Without this line Vite falls back
#    to port 8000 - nexusAuth - and the site can't sign in. Repair it if the file was emptied.
$frontendEnv = Join-Path $studio 'frontend\.env'
$feText = if (Test-Path $frontendEnv) { [IO.File]::ReadAllText($frontendEnv) } else { '' }
if ($feText -notmatch '(?m)^VITE_BACKEND_PROXY_TARGET=http://localhost:8001\s*$') {
    $feText = [regex]::Replace($feText, '(?m)^VITE_BACKEND_PROXY_TARGET=.*\r?\n?', '')
    if ($feText -notmatch '(?m)^VITE_API_BASE_URL=') { $feText = "VITE_API_BASE_URL=`r`n" + $feText }
    [IO.File]::WriteAllText($frontendEnv, $feText.TrimEnd() + "`r`nVITE_BACKEND_PROXY_TARGET=http://localhost:8001`r`n")
    Write-Host 'Repaired frontend\.env (backend address).'
    Stop-Port 5173  # Vite only reads .env when it starts
}

# 1. nexusAuth
if (-not (Test-Port 8000)) {
    Start-Server 'nexusAuth :8000' $nexusAuth '.venv\Scripts\python -m uvicorn main:app --reload --port 8000'
}

# 2. The public address
if ($permanentUrl) {
    $publicUrl = $permanentUrl.TrimEnd('/')
} else {
    if (-not (Test-Port $tunnelMetrics)) {
        Remove-Item $tunnelLog -ErrorAction SilentlyContinue
        Write-Host 'Starting the Cloudflare quick tunnel...'
        Start-Process -FilePath $cloudflared -WindowStyle Minimized -ArgumentList @(
            'tunnel', '--no-autoupdate', '--metrics', "localhost:$tunnelMetrics",
            '--url', 'http://localhost:8090', '--logfile', "`"$tunnelLog`"")
    }
    $publicUrl = $null
    for ($i = 0; $i -lt 60 -and -not $publicUrl; $i++) {
        if (Test-Path $tunnelLog) {
            $m = Select-String -Path $tunnelLog -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches |
                Select-Object -Last 1
            if ($m) { $publicUrl = $m.Matches[-1].Value }
        }
        if (-not $publicUrl) { Start-Sleep 1 }
    }
    if (-not $publicUrl) { Fail "The Cloudflare tunnel did not report an address. Check the internet connection and $tunnelLog." }
}

# 3. Use the public address everywhere (PUBLIC_BASE_URL). Backends read it at startup: restart them if it changed.
$envText = [IO.File]::ReadAllText($envFile)
$current = [regex]::Match($envText, '(?m)^PUBLIC_BASE_URL=(.*?)\r?$').Groups[1].Value
$addressChanged = $current -ne $publicUrl
if ($addressChanged) {
    $envText = [regex]::Replace($envText, '(?m)^PUBLIC_BASE_URL=.*?(\r?)$', "PUBLIC_BASE_URL=$publicUrl`$1")
    [IO.File]::WriteAllText($envFile, $envText)
    Write-Host "PUBLIC_BASE_URL set to $publicUrl (was $current)"
    Stop-Port 8001
    Stop-Port 8090
}

# 4. Admin backend (private), public gateway (behind the public address), admin frontend
if (-not (Test-Port 8001)) {
    Start-Server 'Signature Studio backend :8001' (Join-Path $studio 'backend') '.venv\Scripts\python -m uvicorn app.main:app --reload --port 8001'
}
if (-not (Test-Port 8090)) {
    Start-Server 'Signature Studio public gateway :8090' (Join-Path $studio 'backend') '.venv\Scripts\python -m uvicorn app.public_app:app --port 8090'
}
if (-not (Test-Port 5173)) {
    Start-Server 'Signature Studio frontend :5173' (Join-Path $studio 'frontend') 'npm run dev'
}
if (-not ((Wait-Port 8001) -and (Wait-Port 8090) -and (Wait-Port 5173))) {
    Fail 'Something did not start - check the server windows for errors.'
}

# 5. Check the public address really reaches Signature Studio from the internet
$reachable = $false
for ($i = 0; $i -lt 20 -and -not $reachable; $i++) {
    try { $reachable = (Invoke-WebRequest -Uri "$publicUrl/api/health" -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200 }
    catch { Start-Sleep 3 }
}

Write-Host ''
Write-Host 'Signature Studio is running.' -ForegroundColor Green
Write-Host "  Admin app (this PC):  http://localhost:5173"
Write-Host "  Public address:       $publicUrl" -ForegroundColor Yellow
if (-not $reachable) {
    Write-Host '  WARNING: the public address does not answer yet. Wait a minute and open it in a browser;' -ForegroundColor Red
    Write-Host '  if it still fails, check the internet connection and run this again.' -ForegroundColor Red
}
if ($addressChanged -and -not $permanentUrl) {
    Write-Host ''
    Write-Host '  The public address CHANGED. Everyone must use a new setup link:' -ForegroundColor Yellow
    Write-Host '   1. Signatures > Send email (or copy the setup link) for each employee.'
    Write-Host '   2. They remove the old Casterly add-in in Outlook and add the new manifest,'
    Write-Host '      or run the new classic Outlook installer.'
}
Start-Process 'http://localhost:5173'
Read-Host 'Press Enter to close this window (the servers keep running)'
