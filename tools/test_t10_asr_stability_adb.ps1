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
$completionFunction = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq "Resolve-T10InferenceCompletion"
}, $true)
if ($null -eq $completionFunction) { throw "Resolve-T10InferenceCompletion helper not found." }
. ([scriptblock]::Create($completionFunction.Extent.Text))


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

    # Device log showed 'adb_exit=' (null) although remote result.txt existed:
    # classify as collected but UNVERIFIED rather than fail run=1 or assert PASS.
    $confirmed = Resolve-T10InferenceCompletion -AdbExitCode 0 -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($confirmed -ne "RESULT_PRESENT_EXIT_ZERO") { throw "Exit 0 + transcript must verify." }
    $unknown = Resolve-T10InferenceCompletion -AdbExitCode $null -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($unknown -ne "RESULT_PRESENT_EXIT_UNKNOWN") { throw "Missing ExitCode with transcript classified incorrectly." }
    $unverified = Resolve-T10InferenceCompletion -AdbExitCode 7 -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($unverified -ne "RESULT_PRESENT_ADB_NONZERO") { throw "Nonzero exit with transcript classified incorrectly." }
    $missingWasRejected = $false
    try {
        Resolve-T10InferenceCompletion -AdbExitCode 0 -TranscriptPresent $false -RunNumber 1 -StderrLog $Adb | Out-Null
    } catch {
        $missingWasRejected = $_.Exception.Message -match "no nonempty transcript"
    }
    if (-not $missingWasRejected) { throw "Missing transcript must fail regardless of exit code." }

    Write-Host "PASS: native stderr handled; exit=0/null/7 with transcript and missing transcript classified; EAP restored."
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
# Windows PowerShell forwards the last native exit code (7 from the deliberate
# negative test) to the hosting action unless explicitly reset after assertions.
$global:LASTEXITCODE = 0
exit 0
