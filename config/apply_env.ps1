# Load config/.env into current PowerShell session
# Usage: . .\config\apply_env.ps1

$ErrorActionPreference = "Stop"
$EnvFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $EnvFile)) {
    throw "Missing config/.env"
}

Get-Content $EnvFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $name = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    if ($name -and $value -and -not $value.StartsWith("your_")) {
        Set-Item -Path "Env:$name" -Value $value
    }
}

Write-Host "Loaded config/.env into current session."
