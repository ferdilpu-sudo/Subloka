# Test the actual Android-compatible /system/bin/sh exit-marker syntax on Linux.
# Uses a stub whisper-cli; does not run real ASR or contact an Android device.
$ErrorActionPreference = "Stop"
$source = Join-Path $PSScriptRoot "t10_asr_stability.ps1"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($source, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw "Cannot parse stability script: $($errors | Out-String)" }

$func = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq "New-T10RemoteInferenceCommand"
}, $true)
if ($null -eq $func) { throw "Cannot locate Android remote command builder" }
. ([scriptblock]::Create($func.Extent.Text))

$temp = Join-Path "/tmp" ("t10-remote-marker-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $fake = Join-Path $temp "whisper-cli"
    @'
#!/bin/sh
printf "test transcript\n" > result.txt
exit "$T10_MOCK_RC"
'@ | Set-Content -Path $fake -Encoding Ascii
    & chmod 755 $fake
    if ($LASTEXITCODE -ne 0) { throw "chmod failed" }

    $command = New-T10RemoteInferenceCommand -Directory $temp -SourceLanguage "id"
    foreach ($expected in @(0, 7)) {
        Remove-Item (Join-Path $temp "result.exit") -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $temp "result.txt") -ErrorAction SilentlyContinue
        $env:T10_MOCK_RC = "$expected"
        & sh -c $command
        $actualProcess = $LASTEXITCODE
        $markerFile = Join-Path $temp "result.exit"
        if (-not (Test-Path $markerFile)) { throw "Missing Android-style marker after exit=$expected" }
        $marker = (Get-Content $markerFile -Raw).Trim()
        if ($actualProcess -ne $expected -or $marker -ne "$expected") {
            throw "Remote shell marker mismatch: expected=$expected actual=$actualProcess marker=$marker"
        }
        if (-not (Test-Path (Join-Path $temp "result.txt"))) { throw "Mock transcript not created." }
    }
    Write-Host "PASS: POSIX shell records actual remote whisper exit 0 and 7 in result.exit."
} finally {
    Remove-Item Env:T10_MOCK_RC -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
$global:LASTEXITCODE = 0
exit 0
