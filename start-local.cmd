@echo off
rem Double-click to start nexusAuth + Signature Studio on this PC and publish it to the internet
rem (Cloudflare quick tunnel, or the permanent address set in start-local.ps1).
rem All the work is in start-local.ps1 (next to this file).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local.ps1"
