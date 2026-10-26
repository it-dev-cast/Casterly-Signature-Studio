# Builds the Outlook signature installer with the C# compiler that ships with Windows
# (.NET Framework 4.x). No extra tools needed.
#
#   powershell -ExecutionPolicy Bypass -File installer\build.ps1
#
# Output: backend\app\installer\CasterlySignatureSetup.exe (served by the backend).
# To avoid Windows SmartScreen warnings, code-sign the output with Casterly's certificate:
#   signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a <exe>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe" }
if (-not (Test-Path $csc)) { throw "C# compiler not found. .NET Framework 4.x is required." }

$outDir = Join-Path $root "backend\app\installer"
New-Item -ItemType Directory -Force $outDir | Out-Null
$out = Join-Path $outDir "CasterlySignatureSetup.exe"
$icon = Join-Path $PSScriptRoot "casterly.ico"

$args = @(
  "/nologo", "/optimize+", "/target:winexe", "/platform:anycpu",
  "/out:$out",
  "/reference:System.Web.Extensions.dll", "/reference:System.Windows.Forms.dll"
)
if (Test-Path $icon) { $args += "/win32icon:$icon" }
$args += (Join-Path $PSScriptRoot "SignatureSetup.cs")

& $csc @args
if ($LASTEXITCODE -ne 0) { throw "Build failed." }
Write-Host "Built $out ($((Get-Item $out).Length) bytes)"
