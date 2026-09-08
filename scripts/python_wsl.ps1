# Usage depuis PowerShell : .\scripts\python_wsl.ps1 -m pytest -q
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
Push-Location $taskRoot
try {
    wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh @args
    $taskExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $taskExitCode
