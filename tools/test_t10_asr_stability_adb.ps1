# Regression: Windows PowerShell 5.1 must not treat successful native stderr
# (adb push progress) as a fatal exception under ErrorActionPreference=Stop.
$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "t10_asr_stability.ps1"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($source, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) {
    throw "T10 PowerShell parse failed: $($errors | Out-String)"
}
$func = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq "Adb-Raw"
}, $true)
if ($null -eq $func) { throw "Adb-Raw helper not found." }
. ([scriptblock]::Create($func.Extent.Text))

$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("t10-adb-mock-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $Adb = Join-Path $temp "adb-mock.cmd"
    $DeviceArgs = @()

    # Typical adb push reports progress on stderr but returns success (0).
    @("@echo off", "echo mock-stdout", "echo 1 file pushed, 0 skipped 1>&2", "exit /b 0") |
        Set-Content -Path $Adb -Encoding Ascii
    $out = @(Adb-Raw -Arguments @("push", "local", "remote"))
    if ($out.Count -ne 1 -or [string]$out[0] -ne "mock-stdout") {
        throw "Successful native stderr polluted stdout or interrupted the call: $($out -join '|')"
    }
    if ($script:T10AdbLastExitCode -ne 0) { throw "Expected exit 0." }
    if ($ErrorActionPreference -ne "Stop") { throw "ErrorActionPreference was not restored." }

    # Real failures must still be fatal and retain the native error/exit code.
    @("@echo off", "echo simulated ADB failure 1>&2", "exit /b 7") |
        Set-Content -Path $Adb -Encoding Ascii
    $caught = ""
    try {
        Adb-Raw -Arguments @("push", "local", "remote") | Out-Null
    } catch {
        $caught = $_.Exception.Message
    }
    if ($caught -notmatch "ADB gagal exit=7") {
        throw "Native exit 7 was not rejected correctly: $caught"
    }
    $ignored = @(Adb-Raw -Arguments @("shell", "pidof", "whisper-cli") -AllowFailure)
    if ($script:T10AdbLastExitCode -ne 7) {
        throw "Expected opt-in failure to preserve exit=7."
    }
    Write-Host "PASS: native stderr on exit 0 ignored; exit 7 rejected; opt-in failure works; EAP restored."
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
