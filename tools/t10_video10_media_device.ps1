<#
T10 real >=600-second MP4 MEDIA stage on the installed SubLoka debug app.
Prepare installs app + test APK. Run requires airplane mode/Wi-Fi off and an
actual >=10min video, executes AndroidMediaSource.inspect + decodePcm, collects
metadata-only JSON and deletes device staging video. NOT FULL APP E2E/CP4.
Compatible with Windows PowerShell 5.1 (ADB stderr is nonfatal if exit=0).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Prepare","Run")][string]$Phase,
    [string]$VideoPath = "",
    [string]$WorkDir = ".t10-benchmark",
    [string]$DeviceSerial = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Package = "app.subloka.caption"
$TestClass = "app.subloka.RealVideoTenMinuteMediaTest"
$RemoteDir = "/sdcard/Android/data/$Package/files"
$RemoteVideo = "$RemoteDir/t10-real-video.mp4"

function Resolve-Local([string]$p) {
    if ([System.IO.Path]::IsPathRooted($p)) { return [System.IO.Path]::GetFullPath($p) }
    return [System.IO.Path]::GetFullPath((Join-Path $Root $p))
}

$AdbCommand = Get-Command adb -ErrorAction SilentlyContinue
if ($AdbCommand) {
    $Adb = $AdbCommand.Source
} else {
    $Sdk = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } elseif ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android\Sdk" }
    $Adb = Join-Path $Sdk "platform-tools\adb.exe"
}
if (!(Test-Path -LiteralPath $Adb)) { throw "ADB tidak ditemukan; instal Android SDK Platform-Tools." }
$DeviceArgs = @()
if ($DeviceSerial) {
    if ($DeviceSerial -notmatch '^[A-Za-z0-9._:-]+$') { throw "Serial perangkat tidak aman." }
    $DeviceArgs = @("-s", $DeviceSerial)
}

function Adb-Raw {
    param([string[]]$Arguments,[switch]$AllowFailure)
    $before = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $out = @(& $Adb @DeviceArgs @Arguments 2>&1)
        $result = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $before
    }
    $script:LastAdbExit = $result
    $lines = @($out | ForEach-Object { [string]$_ })
    if ($result -ne 0 -and !$AllowFailure) { throw "ADB exit=$result $($Arguments -join ' '): $($lines -join ' | ')" }
    return $lines
}

function Require-Device {
    $ready = @(Adb-Raw -Arguments @("devices") | Where-Object { $_ -match '^\S+\s+device\s*$' })
    if ($DeviceSerial) {
        if (@($ready | Where-Object { ($_ -split '\s+')[0] -eq $DeviceSerial }).Count -ne 1) {
            throw "Perangkat dengan serial $DeviceSerial tidak ditemukan."
        }
    } elseif ($ready.Count -ne 1) {
        throw "Harus tepat satu perangkat adb 'device', ditemukan $($ready.Count)."
    }
    $sdk = (@(Adb-Raw -Arguments @("shell","getprop","ro.build.version.sdk")) -join "").Trim()
    if ($sdk -notmatch '^\d+$' -or [int]$sdk -lt 26) { throw "SDK Android tidak didukung: $sdk" }
    Write-Host "Perangkat siap: Android SDK $sdk"
}

function Runner-Component {
    $lines = @(Adb-Raw -Arguments @("shell","pm","list","instrumentation"))
    $hits = @()
    foreach ($line in $lines) {
        if ($line -match 'instrumentation:(\S+/\S+)\s+\(target=app\.subloka\.caption\)' -and
            $line.Contains("AndroidJUnitRunner")) { $hits += $Matches[1] }
    }
    if ($hits.Count -ne 1) { throw "AndroidJUnitRunner SubLoka tidak tersedia. Jalankan -Phase Prepare." }
    return $hits[0]
}

function Battery-C {
    $info = @(Adb-Raw -Arguments @("shell","dumpsys","battery")) -join [Environment]::NewLine
    if ($info -notmatch '(?m)^\s*temperature:\s*(\d+)\s*$') { throw "Sensor suhu baterai tidak dilaporkan." }
    $tenths = [int]$Matches[1]
    if ($tenths -lt 100 -or $tenths -gt 600) { throw "Suhu baterai tidak wajar: $tenths" }
    return $tenths / 10.0
}

Require-Device
Push-Location $Root
try {
    if ($Phase -eq "Prepare") {
        Write-Host "PREPARE: build app + instrumentation APK, lalu instal tanpa uninstall." -ForegroundColor Cyan
        & .\gradlew.bat :app:assembleDebug :app:assembleDebugAndroidTest
        if ($LASTEXITCODE -ne 0) { throw "Gradle gagal." }
        $appApk = Join-Path $Root "app\build\outputs\apk\debug\app-debug.apk"
        $testDir = Join-Path $Root "app\build\outputs\apk\androidTest"
        if (!(Test-Path $appApk)) { throw "Debug APK tidak ditemukan: $appApk" }
        $tests = @(Get-ChildItem -LiteralPath $testDir -Recurse -File -Filter "*.apk")
        if ($tests.Count -ne 1) { throw "APK instrumentasi diharapkan satu, ditemukan $($tests.Count)." }
        Adb-Raw -Arguments @("install","-r","-t",$appApk) | ForEach-Object { Write-Host $_ }
        Adb-Raw -Arguments @("install","-r","-t",$tests[0].FullName) | ForEach-Object { Write-Host $_ }
        $runner = Runner-Component
        Write-Host "PREPARE PASS: $runner" -ForegroundColor Green
        Write-Host "Aktifkan airplane mode, Wi-Fi off, suhu baterai <40C, dan sediakan MP4 asli 10–15 menit dengan audio."
        Write-Host '.\tools\t10_video10_media_device.ps1 -Phase Run -VideoPath "C:\video\asli-10-menit.mp4"'
    } else {
        if (!$VideoPath) { throw "Gunakan -VideoPath menunjuk ke video .mp4 asli." }
        $source = Resolve-Local $VideoPath
        if (!(Test-Path -LiteralPath $source -PathType Leaf)) { throw "Video tidak ditemukan: $source" }
        if ([System.IO.Path]::GetExtension($source).ToLowerInvariant() -ne ".mp4") {
            throw "Gunakan berkas .mp4 asli yang memiliki track video dan audio."
        }
        $file = Get-Item -LiteralPath $source
        if ($file.Length -le 0) { throw "Video sumber kosong." }
        $airplane = (@(Adb-Raw -Arguments @("shell","settings","get","global","airplane_mode_on")) -join "").Trim()
        $wifi = (@(Adb-Raw -Arguments @("shell","settings","get","global","wifi_on")) -join "").Trim()
        if ($airplane -ne "1" -or $wifi -ne "0") {
            throw "Mode offline belum siap: airplane=$airplane wifi=$wifi"
        }
        $initial = Battery-C
        if ($initial -ge 40.0) { throw "Suhu baterai awal $initial C; dinginkan sampai <40C." }
        $runner = Runner-Component
        $runId = (Get-Date -Format "yyyyMMddTHHmmss") + "-" + [Guid]::NewGuid().ToString("N").Substring(0,8)
        $outDir = Join-Path (Resolve-Local $WorkDir) ("video10-media-" + $runId)
        New-Item -ItemType Directory -Path $outDir -ErrorAction Stop | Out-Null
        $remoteReportName = "t10-video10-$runId.json"
        $remoteReport = "$RemoteDir/$remoteReportName"
        $jsonOut = Join-Path $outDir "device-media-report.json"
        $stdout = Join-Path $outDir "instrumentation.stdout.txt"
        $stderr = Join-Path $outDir "instrumentation.stderr.txt"
        $sha = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
        [ordered]@{
            evidence_type = "T10_REAL_VIDEO_MEDIA_STAGE_ONLY"
            video_file = $file.Name
            video_bytes = $file.Length
            video_sha256 = $sha
            battery_start_c = $initial
            airplane_mode = $airplane
            wifi_on = $wifi
            runner = $runner
            cp4 = "BLOCKED"
        } | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $outDir "host-preflight.json")
        Write-Host "Session: $outDir" -ForegroundColor Cyan
        Write-Host "SHA256 video asli: $sha"
        $staged = $false
        try {
            Adb-Raw -Arguments @("shell","mkdir","-p",$RemoteDir) | Out-Null
            # Attempt cleanup even if adb push stops halfway through writing the video.
            $staged = $true
            Adb-Raw -Arguments @("push",$source,$RemoteVideo) | ForEach-Object { Write-Host $_ }
            $remoteSize = (@(Adb-Raw -Arguments @("shell","stat","-c","%s",$RemoteVideo)) -join "").Trim()
            if ($remoteSize -ne [string]$file.Length) {
                throw "Ukuran video tidak cocok sesudah adb push: lokal=$($file.Length); device=$remoteSize"
            }
            $argsText = ($DeviceArgs + @("shell","am","instrument","-w","-r",
                "-e","class",$TestClass,"-e","reportName",$remoteReportName,$runner)) -join " "
            $p = Start-Process -FilePath $Adb -ArgumentList $argsText -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
            $finished = $p.WaitForExit(1500000) # 25 minute watchdog
            if (!$finished) {
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                Adb-Raw -Arguments @("shell","am","force-stop",$Package) -AllowFailure | Out-Null
            } else {
                # WinPS 5.1 may not expose a Start-Process exit code after WaitForExit.
                # Require Android's actual completion marker plus a valid device JSON.
                $p.Refresh()
            }
            $adbProcessExitCode = if ($finished) { $p.ExitCode } else { $null }
            $console = if (Test-Path $stdout) { Get-Content -LiteralPath $stdout -Raw } else { "" }
            Write-Host $console
            # Try to recover a FAILED result as well, before deciding pass/fail.
            Adb-Raw -Arguments @("pull",$remoteReport,$jsonOut) -AllowFailure | ForEach-Object { Write-Host $_ }
            if (!$finished) { throw "TIMEOUT 25 menit; laporan mungkin tidak lengkap. Lihat $outDir." }
            $androidPass = ($console -match '(?m)^OK \(1 test\)\s*$' -and
                $console -match '(?m)^INSTRUMENTATION_CODE:\s*-1\s*$')
            if (!$androidPass -or ($null -ne $adbProcessExitCode -and [int]$adbProcessExitCode -ne 0)) {
                throw "Instrumentation FAIL (adb exit=$adbProcessExitCode, android_ok=$androidPass); bukti di $outDir."
            }
            if (!(Test-Path $jsonOut)) { throw "Tidak ada laporan JSON dari perangkat." }
            $report = Get-Content -Raw -LiteralPath $jsonOut | ConvertFrom-Json
            if ($report.status -ne "MEDIA_STAGE_PASS_NOT_FULL_E2E" -or
                $report.full_app_e2e -ne "BLOCKED_ASR_TRANSLATION_RENDER_EXPORT_NOT_INTEGRATED" -or
                $report.source_sha256 -ne $sha -or $report.source_sha256_after -ne $sha -or
                $report.source_unchanged -ne $true -or $report.duration_us -lt 600000000 -or
                $report.pcm_truncated -ne $false -or $report.battery_peak_c -ge 43.0) {
                throw "Status/sha/durasi/PCM/suhu pada JSON tidak valid: $jsonOut"
            }
            Write-Host "MEDIA STAGE PASS (BUKAN full E2E/CP4)." -ForegroundColor Green
            Write-Host "JSON evidence: $jsonOut"
            Write-Host ("SHA256 JSON: " + (Get-FileHash -Algorithm SHA256 $jsonOut).Hash)
            Write-Host ("Lanjut: python tools/t10_video10_media_review.py " +
                (Join-Path $outDir "host-preflight.json") + " " + $jsonOut)
        } finally {
            if ($staged) {
                Adb-Raw -Arguments @("shell","rm","-f",$RemoteVideo) -AllowFailure | Out-Null
                if ($script:LastAdbExit -eq 0) {
                    Write-Host "Video sementara dihapus dari app-specific device storage."
                } else {
                    Write-Warning "Gagal menghapus video sementara. Hapus manual: $RemoteVideo"
                }
            }
        }
    }
} finally {
    Pop-Location
}
