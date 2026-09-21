<#
One-time local setup (Windows, PowerShell). Idempotent: safe to re-run.

  .\scripts\setup.ps1 -DatasetZip "C:\path\Датасет.zip"   # first time: unpack data + everything
  .\scripts\setup.ps1                                     # deps + catalog + index (data already unpacked)
  .\scripts\setup.ps1 -Cpu                                # no NVIDIA GPU

Needs: Python 3.11+, Node 20+, Docker Desktop, 7-Zip (only for -DatasetZip).
#>
param(
  [string]$DatasetZip = "",
  [switch]$Cpu,
  [string]$Model = "google/siglip2-so400m-patch14-384"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Check() { if ($LASTEXITCODE -ne 0) { throw "command failed with exit code $LASTEXITCODE" } }

if ($DatasetZip) {
  Step "Unpacking dataset from $DatasetZip"
  & "$PSScriptRoot\prepare_data.ps1" -DatasetZip $DatasetZip; Check
}

Step "Python venv (ml/.venv)"
if (-not (Test-Path "ml\.venv")) { python -m venv ml\.venv; Check }
$py = "ml\.venv\Scripts\python.exe"
& $py -m pip install -q --upgrade pip; Check
$torchIndex = if ($Cpu) { "https://download.pytorch.org/whl/cpu" } else { "https://download.pytorch.org/whl/cu128" }
& $py -m pip install -q torch --index-url $torchIndex; Check
& $py -m pip install -q -e "ml[dev]" pillow-heif; Check

Step "Web deps (web/node_modules)"
Push-Location web; npm ci; Check; Pop-Location

Step "Postgres + pgvector (docker)"
docker compose up -d --wait db; Check

Step "Catalog: unambiguous positions"
& $py ml\scripts\build_catalog.py; Check
& $py ml\scripts\load_catalog.py; Check

Step "Index: SigLIP 2 embeddings -> pgvector (first run downloads the model, ~4.5 GB)"
$env:MODEL_NAME = $Model
if ($Cpu) { $env:DEVICE = "cpu" }
& $py ml\scripts\build_index.py; Check

Write-Host "`nDone. Start the service: .\scripts\dev.ps1" -ForegroundColor Green
