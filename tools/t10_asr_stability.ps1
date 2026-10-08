<#
T10 offline ASR thermal / stability sampling on a physical Android arm64 device.
Uses the already-built whisper.cpp v1.9.4 artifact and checksum-verified model.
This is a repeated-utterance workload, NOT a 10-minute-video E2E test or CP4 PASS.
#>
[CmdletBinding()]
param(
    [string]$DatasetManifest = "t10-dataset.json",
    [string]$WorkDir = ".t10-benchmark",
    [ValidateSet("base", "tiny")]
    [string]$Model = "base",
    [ValidateSet("id", "en")]
    [string]$Language = "id",
    [ValidateRange(2, 10)]
    [int]$RunMinutes = 5,
    [string]$DeviceSerial = "",
    [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RemoteDir = "/data/local/tmp/subloka-t10-thermal"
$StopTemperatureC = 43.0
$StartTemperatureLimitC = 40.0
$ModelChecksums = @{
    "base" = "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"
    "tiny" = "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21"
}

function Resolve-RepoPath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $Path))
}

$ManifestPath = Resolve-RepoPath $DatasetManifest
$WorkDirectory = Resolve-RepoPath $WorkDir
$Cli = Join-Path $WorkDirectory "build-android/bin/whisper-cli"
$ModelPath = Join-Path $WorkDirectory ("models/ggml-" + $Model + ".bin")
$Tool = Get-Command adb -ErrorAction SilentlyContinue
if ($null -eq $Tool) {
    $Sdk = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } elseif ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android/Sdk" }
    $Adb = Join-Path $Sdk "platform-tools/adb.exe"
} else {
    $Adb = $Tool.Source
}
if (!(Test-Path $Adb)) { throw "ADB tidak tersedia. Instal Android SDK Platform-Tools." }

$DeviceArgs = @()
if ($DeviceSerial) { $DeviceArgs = @("-s", $DeviceSerial) }
function Adb-Raw {
    param(
        [string[]]$Arguments,
        [switch]$AllowFailure
    )
    # Windows PowerShell 5.1 converts native stderr (including successful
    # 'adb push: 1 file pushed') into ErrorRecord. With Stop it aborts
    # before checking the real native exit code. Capture stderr non-fatally.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $Adb @DeviceArgs @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    $script:T10AdbLastExitCode = $exitCode
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "ADB gagal exit=$exitCode ($($Arguments -join ' ')): $($output -join ' ')"
    }
    # Keep stdout as data; stderr is diagnostic only (not a fatal PowerShell error).
    return @($output | Where-Object {
        $_ -isnot [System.Management.Automation.ErrorRecord]
    })
}


function New-T10RemoteInferenceCommand {
    param(
        [string]$Directory,
        [ValidateSet("id", "en")][string]$SourceLanguage
    )
    if ($Directory -notmatch '^/[a-zA-Z0-9/_-]+$') {
        throw "Unsafe remote benchmark directory."
    }
    # The single-quoted PS literal deliberately preserves Android shell $?/$rc.
    # Exit code is written on-device, independent of Windows Start-Process.ExitCode.
    return ('cd {0} && ./whisper-cli -m model.bin -f input.wav -l {1} -nt -ng -nfa -otxt -of result; rc=$?; echo $rc > result.exit; exit $rc' -f $Directory, $SourceLanguage)
}

function Parse-T10RemoteExit {
    param(
        [string[]]$Lines,
        [int]$ReadExitCode
    )
    if ($ReadExitCode -ne 0) { return $null }
    $value = ($Lines -join "").Trim()
    if ($value -notmatch '^(0|[1-9]\d{0,2})$') { return $null }
    $code = [int]$value
    if ($code -gt 255) { return $null }
    return $code
}


function Resolve-T10InferenceCompletion {
    param(
        [AllowNull()][object]$AdbExitCode,
        [AllowNull()][object]$RemoteExitCode,
        [bool]$TranscriptPresent,
        [int]$RunNumber,
        [string]$StderrLog
    )
    if (-not $TranscriptPresent) {
        $diagnostic = ""
        if (Test-Path $StderrLog) {
            $diagnostic = (@(Get-Content -LiteralPath $StderrLog -Tail 8 -ErrorAction SilentlyContinue) -join " | ")
        }
        throw "Inference FAIL run=$RunNumber, no nonempty transcript; adb_exit=$AdbExitCode remote_exit=$RemoteExitCode. stderr tail: $diagnostic"
    }

    # Remote exit marker, written by Android shell, verifies the inference
    # independently from Start-Process.ExitCode (often null in PS 5.1).
    if ($null -eq $RemoteExitCode -or [string]$RemoteExitCode -eq "") {
        Write-Warning ("Run {0}: transcript exists but remote exit marker is missing; result remains unverified." -f $RunNumber)
        return "RESULT_PRESENT_REMOTE_EXIT_UNKNOWN"
    }
    if ([int]$RemoteExitCode -ne 0) {
        Write-Warning ("Run {0}: Whisper returned remote exit {1}, despite a nonempty result." -f $RunNumber, $RemoteExitCode)
        return "RESULT_PRESENT_REMOTE_NONZERO"
    }

    if ($null -eq $AdbExitCode -or [string]$AdbExitCode -eq "") {
        return "RESULT_PRESENT_REMOTE_EXIT_ZERO_ADB_UNKNOWN"
    }
    if ([int]$AdbExitCode -ne 0) {
        return "RESULT_PRESENT_REMOTE_EXIT_ZERO_ADB_NONZERO"
    }
    return "RESULT_PRESENT_EXIT_ZERO"
}


function Get-BatterySnapshot {
    $raw = @(Adb-Raw -Arguments @("shell", "dumpsys battery"))
    $text = $raw -join [Environment]::NewLine
    if ($text -notmatch '(?m)^\s*temperature:\s*(-?\d+)\s*$') {
        throw "Sensor battery.temperature tidak dilaporkan; pengujian panas ditolak."
    }
    $tenths = [int]$Matches[1]
    if ($tenths -lt 150 -or $tenths -gt 600) {
        throw "Suhu baterai tidak masuk akal ($tenths dalam 0.1 C); pengujian dihentikan."
    }
    $plugged = "unknown"
    if ($text -match '(?m)^\s*USB powered:\s*(true|false)\s*$') {
        $plugged = $Matches[1]
    }
    return [pscustomobject]@{
        temperature_c = [Math]::Round($tenths / 10.0, 1)
        usb_powered = $plugged
    }
}

function Get-RemoteRssKb {
    $remoteIds = @(Adb-Raw -Arguments @("shell", "pidof whisper-cli") -AllowFailure)
    if ($script:T10AdbLastExitCode -ne 0 -or $remoteIds.Count -eq 0) { return $null }
    $text = ($remoteIds -join " ").Trim()
    if ($text -notmatch '^\s*(\d+)') { return $null }
    $remoteProcessId = $Matches[1]
    $status = @(Adb-Raw -Arguments @("shell", "grep VmRSS /proc/$remoteProcessId/status 2>/dev/null") -AllowFailure)
    if ($script:T10AdbLastExitCode -ne 0) { return $null }
    if (($status -join " ") -match 'VmRSS:\s*(\d+)\s*kB') {
        return [int]$Matches[1]
    }
    return $null
}

function Stop-RemoteWhisper {
    $remoteIds = @(Adb-Raw -Arguments @("shell", "pidof whisper-cli") -AllowFailure)
    if ($script:T10AdbLastExitCode -ne 0) { return }
    foreach ($candidate in (($remoteIds -join " ") -split '\s+')) {
        if ($candidate -match '^\d+$') {
            Adb-Raw -Arguments @("shell", "kill -TERM $candidate") -AllowFailure | Out-Null
        }
    }
}

if (!(Test-Path $ManifestPath)) { throw "Dataset manifest tidak ditemukan: $ManifestPath" }
if (!(Test-Path $Cli)) {
    throw "whisper-cli belum ada: $Cli. Jalankan benchmark T10 ASR awal terlebih dahulu; script ini tidak rebuild."
}
if (!(Test-Path $ModelPath)) {
    throw "Model $Model belum ada: $ModelPath. Siapkan model melalui harness ASR awal."
}
$ActualModelChecksum = (Get-FileHash $ModelPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualModelChecksum -ne $ModelChecksums[$Model]) { throw "SHA-256 model $Model tidak cocok; pengujian dibatalkan." }

$Dataset = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$Samples = @($Dataset.samples | Where-Object { $_.language -eq $Language } | Sort-Object id)
if ($Samples.Count -lt 1) { throw "Manifest tidak memiliki sampel untuk bahasa $Language." }
$SampleAudio = @()
foreach ($sample in $Samples) {
    if ([string]::IsNullOrWhiteSpace([string]$sample.id) -or [string]::IsNullOrWhiteSpace([string]$sample.audio)) {
        throw "Manifest memuat sampel tanpa ID atau path audio."
    }
    $audio = [System.IO.Path]::GetFullPath((Join-Path (Split-Path $ManifestPath) ([string]$sample.audio)))
    if (!(Test-Path $audio)) { throw "Audio tidak ditemukan untuk $($sample.id): $audio" }
    $seconds = [double]$sample.durationSeconds
    if ($seconds -le 0) { throw "Durasi audio tidak valid untuk $($sample.id)" }
    $SampleAudio += [pscustomobject]@{ id = [string]$sample.id; audio = $audio; duration_s = $seconds }
}

$ready = @(& $Adb devices | Where-Object { $_ -match '^\S+\s+device$' })
if ($DeviceSerial) {
    if ((@($ready | Where-Object { ($_ -split '\s+')[0] -eq $DeviceSerial })).Count -ne 1) {
        throw "Perangkat $DeviceSerial tidak terlihat pada adb devices."
    }
} elseif ($ready.Count -ne 1) {
    throw "Hubungkan tepat satu perangkat siap di ADB, atau berikan -DeviceSerial. Jumlah=$($ready.Count)"
}
$abi = ((Adb-Raw -Arguments @("shell", "getprop ro.product.cpu.abi")) -join " ").Trim()
if ($abi -ne "arm64-v8a") { throw "Diperlukan arm64-v8a, terdeteksi: $abi." }
$airplane = ((Adb-Raw -Arguments @("shell", "settings get global airplane_mode_on")) -join " ").Trim()
$wifi = ((Adb-Raw -Arguments @("shell", "settings get global wifi_on")) -join " ").Trim()
if ($airplane -ne "1" -or $wifi -ne "0") {
    throw "Aktifkan mode pesawat dan matikan Wi-Fi sebelum uji (airplane=$airplane wifi=$wifi)."
}
$InitialBattery = Get-BatterySnapshot
if ($InitialBattery.temperature_c -ge $StartTemperatureLimitC) {
    throw "Suhu awal baterai $($InitialBattery.temperature_c) C terlalu tinggi; tunggu hingga di bawah $StartTemperatureLimitC C."
}

Write-Host "T10 ASR stability preflight OK | $Model/$Language | $($Samples.Count) WAV | arm64 | offline | battery=$($InitialBattery.temperature_c) C"
Write-Host "Catatan: battery temperature bukan suhu CPU. Ini uji repeated utterance, bukan benchmark video 10 menit."
if ($PreflightOnly) {
    Write-Host "PREFLIGHT PASS. File dan perangkat siap; tidak ada inference dijalankan."
    return
}

$SessionName = "thermal-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + "-" + [Guid]::NewGuid().ToString("N").Substring(0, 6)
$OutputDir = Join-Path $WorkDirectory $SessionName
if (Test-Path $OutputDir) { throw "Folder output sudah ada: $OutputDir" }
New-Item -ItemType Directory -Path $OutputDir | Out-Null
$Runs = New-Object 'System.Collections.Generic.List[object]'
$Telemetry = New-Object 'System.Collections.Generic.List[object]'
$Status = "ABORTED"
$AbortReason = $null
$PeakTemperatureC = $InitialBattery.temperature_c
$LastTemperatureC = $InitialBattery.temperature_c
$SessionWatch = [System.Diagnostics.Stopwatch]::StartNew()
$LastRun = 0

try {
    Adb-Raw -Arguments @("shell", "mkdir -p $RemoteDir") | Out-Null
    Adb-Raw -Arguments @("push", $Cli, "$RemoteDir/whisper-cli") | Out-Null
    Adb-Raw -Arguments @("shell", "chmod 755 $RemoteDir/whisper-cli") | Out-Null
    Adb-Raw -Arguments @("push", $ModelPath, "$RemoteDir/model.bin") | Out-Null
    Write-Host "Model and binary transferred to isolated remote benchmark directory."
    $SessionWatch.Restart()

    while ($SessionWatch.Elapsed.TotalMinutes -lt $RunMinutes) {
        $LastRun++
        $item = $SampleAudio[($LastRun - 1) % $SampleAudio.Count]
        $startBattery = Get-BatterySnapshot
        if ($startBattery.temperature_c -ge $StopTemperatureC) {
            throw "THERMAL_STOP: baterai $($startBattery.temperature_c) C mencapai batas $StopTemperatureC C."
        }

        Adb-Raw -Arguments @("push", $item.audio, "$RemoteDir/input.wav") | Out-Null
        Adb-Raw -Arguments @("shell", "rm -f $RemoteDir/result.txt $RemoteDir/result.exit") | Out-Null
        # Unique local logs are kept on failure or unverified ADB exit.
        # Never upload transcript/log contents to GitHub.
        $stdout = Join-Path $OutputDir ("run-{0:D4}-stdout.log" -f $LastRun)
        $stderr = Join-Path $OutputDir ("run-{0:D4}-stderr.log" -f $LastRun)
        $cmd = New-T10RemoteInferenceCommand -Directory $RemoteDir -SourceLanguage $Language
        $startArguments = @($DeviceArgs + @("shell", $cmd))
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        $proc = Start-Process -FilePath $Adb -ArgumentList $startArguments -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $runPeakRss = 0
        $tempReadings = 0
        $temperatureFailures = 0
        $adbExit = $null
        try {
            while (!$proc.HasExited) {
                $rss = Get-RemoteRssKb
                if ($null -ne $rss) { $runPeakRss = [Math]::Max($runPeakRss, [int]$rss) }
                try {
                    $battery = Get-BatterySnapshot
                    $temperatureFailures = 0
                    $tempReadings++
                    $LastTemperatureC = $battery.temperature_c
                    $PeakTemperatureC = [Math]::Max($PeakTemperatureC, $battery.temperature_c)
                    $Telemetry.Add([pscustomobject]@{
                        run = $LastRun
                        elapsed_session_s = [Math]::Round($SessionWatch.Elapsed.TotalSeconds, 2)
                        battery_temperature_c = $battery.temperature_c
                        rss_kb = if ($null -eq $rss) { $null } else { [int]$rss }
                    })
                    if ($battery.temperature_c -ge $StopTemperatureC) {
                        Stop-RemoteWhisper
                        throw "THERMAL_STOP: baterai $($battery.temperature_c) C mencapai batas $StopTemperatureC C."
                    }
                } catch {
                    if ($_.Exception.Message -match 'THERMAL_STOP') { throw }
                    $temperatureFailures++
                    if ($temperatureFailures -ge 3) {
                        Stop-RemoteWhisper
                        throw "THERMAL_STOP: 3 pembacaan suhu baterai berturut-turut gagal."
                    }
                }
                Start-Sleep -Milliseconds 1000
                $proc.Refresh()
            }
        } finally {
            # Wait without a timeout before reading ExitCode. Merely observing
            # HasExited is insufficient on some Windows PowerShell 5.1 builds.
            if (-not $proc.WaitForExit(5000)) {
                # This path is normally only reached after a thermal/error abort.
                # Ensure a stuck local adb process cannot hold the test indefinitely.
                try { $proc.Kill() } catch {}
                $proc.WaitForExit(5000) | Out-Null
            }
            try {
                $proc.Refresh()
                if ($proc.HasExited) { $adbExit = $proc.ExitCode }
            } catch { $adbExit = $null }
            $timer.Stop()
        }
        $hasOutput = @(Adb-Raw -Arguments @("shell", "test -s $RemoteDir/result.txt") -AllowFailure)
        $outputExit = $script:T10AdbLastExitCode
        # Capture a separate Android-shell exit marker for the actual inference.
        # Preserve the ADB cat exit status immediately (later ADB calls replace it).
        $markerLines = @(Adb-Raw -Arguments @("shell", "cat $RemoteDir/result.exit") -AllowFailure)
        $markerReadExit = $script:T10AdbLastExitCode
        $remoteExit = Parse-T10RemoteExit -Lines $markerLines -ReadExitCode $markerReadExit
        $completion = Resolve-T10InferenceCompletion -AdbExitCode $adbExit -RemoteExitCode $remoteExit -TranscriptPresent ($outputExit -eq 0) -RunNumber $LastRun -StderrLog $stderr
        if ($completion -eq "RESULT_PRESENT_REMOTE_NONZERO") {
            throw ("Inference FAIL run={0}: Android Whisper process returned exit={1}, with transcript present. See {2}." -f $LastRun, $remoteExit, $stderr)
        }
        if ($completion -eq "RESULT_PRESENT_EXIT_ZERO") {
            Remove-Item $stdout, $stderr -Force -ErrorAction SilentlyContinue
        }
        $endBattery = Get-BatterySnapshot
        $LastTemperatureC = $endBattery.temperature_c
        $PeakTemperatureC = [Math]::Max($PeakTemperatureC, $endBattery.temperature_c)
        $elapsed = $timer.Elapsed.TotalSeconds
        $rtf = $elapsed / $item.duration_s
        $Runs.Add([pscustomobject]@{
            run = $LastRun
            sample = $item.id
            model = $Model
            language = $Language
            duration_s = $item.duration_s
            elapsed_s = [Math]::Round($elapsed, 3)
            rtf = [Math]::Round($rtf, 4)
            peak_rss_kb = if ($runPeakRss -gt 0) { $runPeakRss } else { $null }
            temp_start_c = $startBattery.temperature_c
            temp_end_c = $endBattery.temperature_c
            temp_samples = $tempReadings
            adb_exit_code = $adbExit
            remote_exit_code = $remoteExit
            completion_evidence = $completion
        })
        Write-Host ("Run {0} {1}: {2:N2}s, RTF={3:N2}, battery={4:N1}C, peakRSS={5}kB, remoteExit={6}, adbExit={7}, evidence={8}" -f $LastRun, $item.id, $elapsed, $rtf, $endBattery.temperature_c, $runPeakRss, $remoteExit, $adbExit, $completion)
        if ($endBattery.temperature_c -ge $StopTemperatureC) {
            throw "THERMAL_STOP: suhu setelah run $LastRun adalah $($endBattery.temperature_c) C (batas $StopTemperatureC C)."
        }
    }
    $remoteUnknown = @($Runs | Where-Object { $_.completion_evidence -eq "RESULT_PRESENT_REMOTE_EXIT_UNKNOWN" }).Count
    $adbUnknown = @($Runs | Where-Object { $_.completion_evidence -in @("RESULT_PRESENT_REMOTE_EXIT_ZERO_ADB_UNKNOWN", "RESULT_PRESENT_REMOTE_EXIT_ZERO_ADB_NONZERO") }).Count
    if ($remoteUnknown -gt 0) {
        $Status = "COLLECTED_WITH_UNVERIFIED_REMOTE_EXIT"
        Write-Warning "$remoteUnknown run(s) have missing Android exit markers; inference completion is not fully verified."
    } elseif ($adbUnknown -gt 0) {
        $Status = "COLLECTED_REMOTE_VERIFIED_ADB_UNVERIFIED"
        Write-Warning "$adbUnknown run(s) verified Whisper exit=0 on Android, but Windows ADB process exit remains unknown/nonzero."
    } else {
        $Status = "COLLECTED_NOT_GATE_PASS"
    }
} catch {
    $AbortReason = $_.Exception.Message
    Write-Warning "T10 stability test berhenti: $AbortReason"
} finally {
    $SessionWatch.Stop()
    if ($Runs.Count -gt 0) {
        $Runs.ToArray() | Export-Csv (Join-Path $OutputDir "runs.csv") -NoTypeInformation -Encoding UTF8
    }
    if ($Telemetry.Count -gt 0) {
        $Telemetry.ToArray() | Export-Csv (Join-Path $OutputDir "telemetry.csv") -NoTypeInformation -Encoding UTF8
    }
    $endBattery = $null
    try { $endBattery = Get-BatterySnapshot; $LastTemperatureC = $endBattery.temperature_c } catch {}
    $rfts = @($Runs | ForEach-Object { [double]$_.rtf } | Sort-Object)
    $median = $null
    $p95 = $null
    if ($rfts.Count -gt 0) {
        $center = [int][Math]::Floor($rfts.Count / 2)
        $median = if (($rfts.Count % 2) -eq 0) { ($rfts[$center - 1] + $rfts[$center]) / 2.0 } else { $rfts[$center] }
        $p95 = $rfts[[int][Math]::Ceiling($rfts.Count * 0.95) - 1]
    }
    $rssValues = @($Runs | Where-Object { $null -ne $_.peak_rss_kb } | ForEach-Object { [int]$_.peak_rss_kb })
    $peakRss = if ($rssValues.Count -gt 0) { ($rssValues | Measure-Object -Maximum).Maximum } else { $null }
    $unverifiedExitRuns = @($Runs | Where-Object { $null -eq $_.adb_exit_code -or $_.adb_exit_code -ne 0 }).Count
    $remoteVerifiedRuns = @($Runs | Where-Object { $null -ne $_.remote_exit_code -and $_.remote_exit_code -eq 0 }).Count
    $remoteUnknownRuns = @($Runs | Where-Object { $null -eq $_.remote_exit_code }).Count
    $ResolvedSerial = if ($DeviceSerial) { $DeviceSerial } else { (($ready[0] -split '\s+')[0]) }
    $DeviceModel = "unavailable"
    $AndroidRelease = "unavailable"
    try { $DeviceModel = ((Adb-Raw -Arguments @("shell", "getprop ro.product.model")) -join " ").Trim() } catch {}
    try { $AndroidRelease = ((Adb-Raw -Arguments @("shell", "getprop ro.build.version.release")) -join " ").Trim() } catch {}
    $summary = [ordered]@{
        evidence = "T10 ASR repeated-utterance thermal/stability PROXY; not E2E 10-minute video"
        status = $Status
        stop_reason = $AbortReason
        duration_requested_minutes = $RunMinutes
        elapsed_session_s = [Math]::Round($SessionWatch.Elapsed.TotalSeconds, 2)
        model = $Model
        model_sha256 = $ActualModelChecksum
        whisper_version = "v1.9.4"
        language = $Language
        fixture_manifest_sha256 = (Get-FileHash $ManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
        completed_runs = $Runs.Count
        unverified_adb_exit_runs = $unverifiedExitRuns
        verified_remote_whisper_exit_zero_runs = $remoteVerifiedRuns
        unverified_remote_whisper_exit_runs = $remoteUnknownRuns
        rtf_median = $median
        rtf_p95_nearest_rank = $p95
        observed_peak_rss_kb = $peakRss
        battery_temp_start_c = $InitialBattery.temperature_c
        battery_temp_peak_c = $PeakTemperatureC
        battery_temp_last_c = $LastTemperatureC
        battery_usb_powered_start = $InitialBattery.usb_powered
        thermal_stop_threshold_c = $StopTemperatureC
        device_serial = $ResolvedSerial
        device_model = $DeviceModel
        android_release = $AndroidRelease
        offline_preflight = "airplane_mode_on=1;wifi_on=0"
        limitations = "Battery temperature is a proxy, not CPU die temperature. Sampled RSS may miss peaks. Includes adb overhead. Android shell writes result.exit separately from Windows ADB process exit. Remote exit=0 plus nonempty transcript verifies CLI process completion, but an unknown/nonzero Windows ADB exit remains explicitly unverified. Repeated short utterances do not establish E2E video stability, app ANR, or CP4 PASS."
    }
    $summary | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $OutputDir "summary.json") -Encoding UTF8
    try { Adb-Raw -Arguments @("shell", "rm -rf $RemoteDir") | Out-Null } catch { Write-Warning "Remote benchmark cache tidak berhasil dibersihkan: $RemoteDir" }
    Write-Host "Output T10: $OutputDir"
    Write-Host ("Status={0}, completed runs={1}, peak battery={2:N1} C, median RTF={3}" -f $Status, $Runs.Count, $PeakTemperatureC, $median)
}
if ($Status -eq "ABORTED") { throw "T10 stability measurement aborted: $AbortReason. See $OutputDir/summary.json" }
