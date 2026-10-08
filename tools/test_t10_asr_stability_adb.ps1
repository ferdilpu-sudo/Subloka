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

foreach ($functionName in @("New-T10RemoteInferenceCommand", "Parse-T10RemoteExit")) {
    $found = $ast.Find({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -eq $functionName
    }, $true)
    if ($null -eq $found) { throw "Missing helper: $functionName" }
    . ([scriptblock]::Create($found.Extent.Text))
}

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

    # Android's own shell must write the status independently of
    # Windows PowerShell 5.1 Start-Process.ExitCode (null on the Sony).
    $remoteCommand = New-T10RemoteInferenceCommand -Directory "/data/local/tmp/subloka-t10-thermal" -SourceLanguage "id"
    if (-not $remoteCommand.Contains('rc=$?; echo $rc > result.exit; exit $rc')) {
        throw "Android remote exit marker command is absent or interpolated by PowerShell."
    }
    if ((Parse-T10RemoteExit -Lines @("0") -ReadExitCode 0) -ne 0) {
        throw "Valid remote exit zero was not parsed."
    }
    if ((Parse-T10RemoteExit -Lines @("17") -ReadExitCode 0) -ne 17) {
        throw "Valid nonzero exit was not parsed."
    }
    if ($null -ne (Parse-T10RemoteExit -Lines @("abc") -ReadExitCode 0)) {
        throw "Malformed exit marker must be unknown."
    }
    if ($null -ne (Parse-T10RemoteExit -Lines @("0") -ReadExitCode 1)) {
        throw "ADB cat failure cannot become a verified remote exit."
    }
    if ($null -ne (Parse-T10RemoteExit -Lines @("256") -ReadExitCode 0)) {
        throw "Remote exit marker outside shell range must be rejected."
    }
    $confirmed = Resolve-T10InferenceCompletion -AdbExitCode 0 -RemoteExitCode 0 -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($confirmed -ne "RESULT_PRESENT_EXIT_ZERO") { throw "ADB+remote zero with transcript must verify." }
    $adbUnknown = Resolve-T10InferenceCompletion -AdbExitCode $null -RemoteExitCode 0 -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($adbUnknown -ne "RESULT_PRESENT_REMOTE_EXIT_ZERO_ADB_UNKNOWN") {
        throw "Android exit zero must remain evidenced if Windows ADB code is missing."
    }
    $adbNonzero = Resolve-T10InferenceCompletion -AdbExitCode 7 -RemoteExitCode 0 -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($adbNonzero -ne "RESULT_PRESENT_REMOTE_EXIT_ZERO_ADB_NONZERO") {
        throw "ADB transport nonzero must remain visible."
    }
    $remoteUnknown = Resolve-T10InferenceCompletion -AdbExitCode 0 -RemoteExitCode $null -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($remoteUnknown -ne "RESULT_PRESENT_REMOTE_EXIT_UNKNOWN") { throw "Missing Android marker must not PASS." }
    $remoteNonzero = Resolve-T10InferenceCompletion -AdbExitCode 0 -RemoteExitCode 17 -TranscriptPresent $true -RunNumber 1 -StderrLog $Adb
    if ($remoteNonzero -ne "RESULT_PRESENT_REMOTE_NONZERO") { throw "Android nonzero must not PASS." }
    $missingWasRejected = $false
    try {
        Resolve-T10InferenceCompletion -AdbExitCode 0 -RemoteExitCode 0 -TranscriptPresent $false -RunNumber 1 -StderrLog $Adb | Out-Null
    } catch {
        $missingWasRejected = $_.Exception.Message -match "no nonempty transcript"
    }
    if (-not $missingWasRejected) { throw "Missing transcript must fail even when both exit codes are zero." }

    Write-Host "PASS: native stderr, Android exit marker, adb exit 0/null/7, transcript missing, malformed remote exit, EAP restored."
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
# Windows PowerShell forwards the last native exit code (7 from the deliberate
# negative test) to the hosting action unless explicitly reset after assertions.
$global:LASTEXITCODE = 0
exit 0
