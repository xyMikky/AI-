# Sync config/.env -> Windows User environment variables
# Run once from project root:
#   powershell -ExecutionPolicy Bypass -File .\config\sync_system_env.ps1

$ErrorActionPreference = "Stop"
$EnvFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $EnvFile)) {
    throw "Missing config/.env"
}

$synced = New-Object System.Collections.Generic.List[string]
Get-Content $EnvFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $name = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    if (-not $name -or -not $value -or $value.StartsWith("your_")) { return }

    [Environment]::SetEnvironmentVariable($name, $value, "User")
    Set-Item -Path "Env:$name" -Value $value
    [void]$synced.Add($name)
}

if ($synced.Count -eq 0) {
    Write-Warning "No keys synced. Check config/.env placeholders."
} else {
    Write-Host ("Synced to User env: " + ($synced -join ", "))
    Write-Host "Restart open terminals / Codex / Cursor to pick up changes."
}
