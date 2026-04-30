param(
    # Path to a scripted input file. Relative paths are resolved from AI\scripts first.
    [Parameter(Mandatory = $true)]
    [string]$TestFile,

    # Interval between scripted input lines (ms). Defaults to env DEBUG_SCRIPTED_INPUT_DELAY_MS or 12000.
    [int]$DelayMs = 0,

    # Initial delay before sending the first line (ms). Defaults to env DEBUG_SCRIPTED_INPUT_START_DELAY_MS or 3000.
    [int]$StartDelayMs = 0,

    # Extra buffer time after last line is sent (sec).
    [int]$BufferSec = 6,

    # Extra runtime padding (sec) to avoid stopping MCP while long TTS/commands are still in-flight.
    # Defaults to env DEBUG_SCRIPTED_INPUT_EXTRA_RUNTIME_SEC or 60.
    [int]$ExtraRuntimeSec = 0,

    # Load additional env vars from a local env file (not committed).
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

function Resolve-PathPreferScripts {
    param([string]$Path, [string]$ScriptsDir, [string]$FallbackDir)

    if (-not $Path) { return "" }
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }

    $p1 = Join-Path $ScriptsDir $Path
    if (Test-Path $p1) { return $p1 }

    if ($FallbackDir) {
        $p2 = Join-Path $FallbackDir $Path
        if (Test-Path $p2) { return $p2 }
    }

    return $p1
}

function Get-ScriptedLinesCount {
    param([string]$Path)

    $count = 0
    $lines = [System.IO.File]::ReadAllLines($Path, [System.Text.Encoding]::UTF8)
    foreach ($raw in $lines) {
        $t = $raw.Trim()
        if (-not $t) { continue }
        if ($t.StartsWith("#")) { continue }
        $count++
    }
    return $count
}

function Get-TestDirectives {
    param([string]$Path)

    # Parse `# key=value` directives from the top of the test file (UTF-8).
    # Example:
    #   # delay_ms=25000
    #   # start_delay_ms=3000
    #   # buffer_sec=10
    #   # extra_runtime_sec=60
    $directives = @{}
    $lines = [System.IO.File]::ReadLines($Path, [System.Text.Encoding]::UTF8)
    $i = 0
    foreach ($raw in $lines) {
        $i++
        if ($i -gt 40) { break }

        $t = $raw.Trim()
        if (-not $t) { continue }
        if (-not $t.StartsWith("#")) { break }

        if ($t -match "^\s*#\s*([a-zA-Z0-9_]+)\s*=\s*([0-9]+)\s*$") {
            $directives[$Matches[1].ToLowerInvariant()] = [int]$Matches[2]
        }
    }
    return $directives
}

function Stop-McpChrome {
    # Match only the Chrome instance started by MCP (unique profile dir marker).
    # Avoid relying on the full path because some consoles/logs show mojibake for non-ASCII path segments.
    Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
        Where-Object { $_.CommandLine -and $_.CommandLine -like '*mcp_chrome_profile*' } |
        ForEach-Object {
            Write-Host ("Stopping Chrome (MCP profile) pid={0}" -f $_.ProcessId)
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

function Stop-ExistingMcpMain {
    # Ensure tests start from a clean state to avoid cross-test flakiness
    # (e.g. "Found existing Chrome CDP at port 9222").
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -and $_.CommandLine -like '*\\MCP\\main.py*' } |
        ForEach-Object {
            Write-Host ("Stopping existing MCP python pid={0}" -f $_.ProcessId) -ForegroundColor Yellow
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

$aiRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $aiRoot
$mcpRoot = Join-Path $workspaceRoot "MCP"
$mcpDebugDir = Join-Path $mcpRoot "debug"

if (-not $LocalEnvFile) {
    $LocalEnvFile = Join-Path $PSScriptRoot "mcp_scripted_input.local.env"
}
Load-EnvFile -Path $LocalEnvFile

$resolvedTestFile = Resolve-PathPreferScripts -Path $TestFile -ScriptsDir $PSScriptRoot -FallbackDir $mcpDebugDir
if (-not (Test-Path $resolvedTestFile)) {
    throw "Test file not found: $resolvedTestFile"
}

$directives = Get-TestDirectives -Path $resolvedTestFile

Stop-ExistingMcpMain
Stop-McpChrome

$env:DEBUG_SCRIPTED_INPUT = "1"
$env:DEBUG_SCRIPTED_INPUT_FILE = $resolvedTestFile

# Precedence:
# 1) CLI params
# 2) test-file directives
# 3) local env file / existing env vars
# 4) defaults
if ($DelayMs -gt 0) {
    $env:DEBUG_SCRIPTED_INPUT_DELAY_MS = "$DelayMs"
} elseif ($directives.ContainsKey("delay_ms")) {
    $env:DEBUG_SCRIPTED_INPUT_DELAY_MS = "$($directives["delay_ms"])"
} elseif (-not $env:DEBUG_SCRIPTED_INPUT_DELAY_MS) {
    $env:DEBUG_SCRIPTED_INPUT_DELAY_MS = "12000"
}

if ($StartDelayMs -gt 0) {
    $env:DEBUG_SCRIPTED_INPUT_START_DELAY_MS = "$StartDelayMs"
} elseif ($directives.ContainsKey("start_delay_ms")) {
    $env:DEBUG_SCRIPTED_INPUT_START_DELAY_MS = "$($directives["start_delay_ms"])"
} elseif (-not $env:DEBUG_SCRIPTED_INPUT_START_DELAY_MS) {
    $env:DEBUG_SCRIPTED_INPUT_START_DELAY_MS = "3000"
}

if (-not $PSBoundParameters.ContainsKey("BufferSec") -and $directives.ContainsKey("buffer_sec")) {
    $BufferSec = $directives["buffer_sec"]
}

if ($ExtraRuntimeSec -le 0 -and $directives.ContainsKey("extra_runtime_sec")) {
    $ExtraRuntimeSec = $directives["extra_runtime_sec"]
}

$delaySec = [double]$env:DEBUG_SCRIPTED_INPUT_DELAY_MS / 1000.0
$startDelaySec = [double]$env:DEBUG_SCRIPTED_INPUT_START_DELAY_MS / 1000.0
$linesCount = Get-ScriptedLinesCount -Path $resolvedTestFile

if ($ExtraRuntimeSec -le 0) {
    if ($env:DEBUG_SCRIPTED_INPUT_EXTRA_RUNTIME_SEC) {
        try { $ExtraRuntimeSec = [int]$env:DEBUG_SCRIPTED_INPUT_EXTRA_RUNTIME_SEC } catch { $ExtraRuntimeSec = 60 }
    } else {
        $ExtraRuntimeSec = 60
    }
}

$expectedSec = [Math]::Ceiling($startDelaySec + ($linesCount * $delaySec) + $BufferSec + $ExtraRuntimeSec)

Write-Host "Running MCP scripted test:" -ForegroundColor Cyan
Write-Host "  MCP_ROOT=$mcpRoot"
Write-Host "  TEST_FILE=$resolvedTestFile"
Write-Host "  LINES=$linesCount delay=${delaySec}s start_delay=${startDelaySec}s buffer=${BufferSec}s extra=${ExtraRuntimeSec}s"
Write-Host "  EXPECTED_RUNTIME=${expectedSec}s"

Push-Location $mcpRoot
try {
    $pythonPath = Join-Path $mcpRoot "venv\\Scripts\\python.exe"
    if (-not (Test-Path $pythonPath)) {
        throw "MCP venv python not found at $pythonPath"
    }

    # Start MCP as a child process so we can reliably terminate it after the test run.
    $p = Start-Process -FilePath $pythonPath -ArgumentList @(".\\main.py") -WorkingDirectory $mcpRoot -PassThru
    Write-Host ("Started MCP pid={0}" -f $p.Id)

    Start-Sleep -Seconds $expectedSec
}
finally {
    Pop-Location

    if ($p -and -not $p.HasExited) {
        Write-Host ("Stopping MCP pid={0}" -f $p.Id) -ForegroundColor Yellow
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }

    Stop-McpChrome
}

Write-Host "Done." -ForegroundColor Green
