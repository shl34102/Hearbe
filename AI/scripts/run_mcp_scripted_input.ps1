param(
    [string]$InputFile = "",
    [int]$DelayMs = 0,
    [string]$LocalEnvFile = ""
)

$ErrorActionPreference = "Stop"

function Load-EnvFile {
    param([string]$Path)

    if (-not $Path) { return }
    if (-not (Test-Path $Path)) { return }

    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }

        # Accept KEY=VALUE lines. Quotes around VALUE are optional.
        if ($line -match "^\s*([^=\s]+)\s*=\s*(.*)\s*$") {
            $key = $Matches[1]
            $val = $Matches[2]

            if ($val.Length -ge 2) {
                $q1 = $val.Substring(0, 1)
                $q2 = $val.Substring($val.Length - 1, 1)
                if (($q1 -eq '"' -and $q2 -eq '"') -or ($q1 -eq "'" -and $q2 -eq "'")) {
                    $val = $val.Substring(1, $val.Length - 2)
                }
            }

            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

$aiRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $aiRoot
$mcpRoot = Join-Path $workspaceRoot "MCP"
$mcpDebugDir = Join-Path $mcpRoot "debug"

function Resolve-InputFilePath {
    param([string]$Path)

    if (-not $Path) { return "" }
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }

    # Prefer a local file next to this launcher (AI\scripts) so each dev can keep
    # their own scripted inputs without touching MCP\debug.
    $candidate1 = Join-Path $PSScriptRoot $Path
    if (Test-Path $candidate1) { return $candidate1 }

    # Backward-compatible fallback: allow using the historical MCP\debug location.
    $candidate2 = Join-Path $mcpDebugDir $Path
    if (Test-Path $candidate2) { return $candidate2 }

    # Default to the launcher-local path even if missing; MCP will log a warning.
    return $candidate1
}

if (-not $LocalEnvFile) {
    $LocalEnvFile = Join-Path $PSScriptRoot "mcp_scripted_input.local.env"
}
Load-EnvFile -Path $LocalEnvFile

$env:DEBUG_SCRIPTED_INPUT = "1"

if ($InputFile) {
    $env:DEBUG_SCRIPTED_INPUT_FILE = Resolve-InputFilePath -Path $InputFile
} elseif (-not $env:DEBUG_SCRIPTED_INPUT_FILE) {
    $env:DEBUG_SCRIPTED_INPUT_FILE = Resolve-InputFilePath -Path "scripted_input.txt"
}

# If DEBUG_SCRIPTED_INPUT_FILE is set but relative (e.g. via local env file),
# resolve it relative to AI\scripts first, then MCP\debug.
if ($env:DEBUG_SCRIPTED_INPUT_FILE -and -not [System.IO.Path]::IsPathRooted($env:DEBUG_SCRIPTED_INPUT_FILE)) {
    $env:DEBUG_SCRIPTED_INPUT_FILE = Resolve-InputFilePath -Path $env:DEBUG_SCRIPTED_INPUT_FILE
}

if ($DelayMs -gt 0) {
    $env:DEBUG_SCRIPTED_INPUT_DELAY_MS = "$DelayMs"
} elseif (-not $env:DEBUG_SCRIPTED_INPUT_DELAY_MS) {
    $env:DEBUG_SCRIPTED_INPUT_DELAY_MS = "12000"
}

Write-Host "Starting MCP scripted-input:" -ForegroundColor Cyan
Write-Host "  MCP_ROOT=$mcpRoot"
Write-Host "  DEBUG_SCRIPTED_INPUT=$env:DEBUG_SCRIPTED_INPUT"
Write-Host "  DEBUG_SCRIPTED_INPUT_FILE=$env:DEBUG_SCRIPTED_INPUT_FILE"
Write-Host "  DEBUG_SCRIPTED_INPUT_DELAY_MS=$env:DEBUG_SCRIPTED_INPUT_DELAY_MS"

Set-Location $mcpRoot

if (-not (Test-Path ".\\venv\\Scripts\\python.exe")) {
    throw "MCP venv python not found at .\\venv\\Scripts\\python.exe"
}

& .\\venv\\Scripts\\python.exe .\\main.py
