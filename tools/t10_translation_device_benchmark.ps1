param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Prepare", "Benchmark")]
    [string]$Phase,
    [string]$OutputPath = ".t10-benchmark/translation-results.csv"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$TestNamespace = "app.subloka.engine.translation"
$RunnerMarker = "AndroidJUnitRunner"

function Require-SingleDevice {
    if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
        throw "adb tidak ditemukan pada PATH."
    }
    $devices = @(& adb devices | Select-String '^\S+\s+device$')
    if ($devices.Count -ne 1) {
        throw "Hubungkan tepat satu perangkat dengan status device. adb devices: $($devices.Count) perangkat siap."
    }
    Write-Host ("ADB device: " + $devices[0].Line)
}

function Get-InstrumentationComponent {
    $list = @(& adb shell pm list instrumentation)
    if ($LASTEXITCODE -ne 0) {
        throw "Gagal membaca instrumentation package pada perangkat."
    }
    $candidates = @()
    foreach ($line in $list) {
        if ($line -match 'instrumentation:(\S+/\S+)\s+\(target=' -and
            $line.Contains($TestNamespace) -and $line.Contains($RunnerMarker)) {
            $candidates += $Matches[1]
        }
    }
    if ($candidates.Count -ne 1) {
        throw "Instrumentation translation tidak ditemukan atau ambigu. Periksa output: adb shell pm list instrumentation"
    }
    return $candidates[0]
}

function Invoke-T10Test([string]$Component, [string]$ClassName) {
    Write-Host "Menjalankan $ClassName" -ForegroundColor Cyan
    $result = @(& adb shell am instrument -w -r -e class $ClassName $Component 2>&1)
    $exit = $LASTEXITCODE
    foreach ($line in $result) { Write-Host $line }
    $combined = $result -join [Environment]::NewLine
    if ($exit -ne 0 -or $combined -notmatch '(?m)^OK \(\d+ tests?\)') {
        throw "Android instrumentation FAIL ($ClassName). Periksa pesan di atas."
    }
}

Push-Location $RepoRoot
try {
    Require-SingleDevice

    if ($Phase -eq "Prepare") {
        Write-Host "PHASE PREPARE: aktifkan internet; APK di-install sekali dan tidak dihapus setelah tes." -ForegroundColor Cyan
        & .\gradlew.bat :engine:translation:assembleDebugAndroidTest
        if ($LASTEXITCODE -ne 0) { throw "Gradle gagal membuat Android test APK." }

        $apkDirectory = Join-Path $RepoRoot "engine/translation/build/outputs/apk/androidTest"
        $apks = @(Get-ChildItem $apkDirectory -Recurse -File -Filter "*.apk" -ErrorAction Stop)
        if ($apks.Count -ne 1) {
            throw "Harus tepat satu androidTest APK, ditemukan $($apks.Count). Periksa $apkDirectory"
        }
        & adb install -r -t $apks[0].FullName
        if ($LASTEXITCODE -ne 0) { throw "adb install gagal." }

        $component = Get-InstrumentationComponent
        Invoke-T10Test $component "$TestNamespace.MlKitTranslationInstrumentedTest"

        Write-Host ""
        Write-Host "PREPARE PASS: model telah disiapkan oleh smoke test." -ForegroundColor Green
        Write-Host "Selanjutnya: aktifkan mode pesawat, matikan Wi-Fi, lalu jalankan:" -ForegroundColor Yellow
        Write-Host ".\tools\t10_translation_device_benchmark.ps1 -Phase Benchmark"
        Write-Host "Jangan jalankan connectedDebugAndroidTest atau uninstall aplikasi di antara kedua fase."
    } else {
        # Deliberately DO NOT install/reinstall or invoke Gradle in benchmark phase.
        $airplane = (& adb shell settings get global airplane_mode_on | Out-String).Trim()
        $wifi = (& adb shell settings get global wifi_on | Out-String).Trim()
        if ($airplane -ne "1") {
            throw "Mode pesawat belum aktif. Aktifkan melalui pengaturan Sony lalu ulangi."
        }
        if ($wifi -ne "0") {
            throw "Wi-Fi belum terkonfirmasi mati (wifi_on=$wifi). Matikan Wi-Fi lalu ulangi."
        }
        $component = Get-InstrumentationComponent
        $destination = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $OutputPath))
        if (Test-Path $destination) {
            throw "File tujuan sudah ada, tidak ditimpa: $destination"
        }

        & adb logcat -c
        if ($LASTEXITCODE -ne 0) { throw "Gagal membersihkan logcat." }
        Invoke-T10Test $component "$TestNamespace.MlKitTranslationBenchmarkTest"

        $log = @(& adb logcat -d -s 'SubLokaT10:I' '*:S')
        if ($LASTEXITCODE -ne 0) { throw "Gagal membaca logcat." }
        $paths = @()
        foreach ($line in $log) {
            if ($line -match 'RESULT_PATH=(\S+\.csv)') {
                $paths += $Matches[1]
            }
        }
        if ($paths.Count -ne 1) {
            throw "Expected exactly one RESULT_PATH in logcat, got $($paths.Count). Periksa adb logcat -d -s SubLokaT10:I '*:S'"
        }
        $remote = $paths[0]
        $parentDir = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
        & adb pull $remote $destination
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $destination)) {
            throw "adb pull gagal untuk $remote"
        }
        Write-Host "BENCHMARK PASS: CSV tersimpan di $destination" -ForegroundColor Green
        Write-Host ("Selanjutnya: python tools/t10_translation_review.py init " + $destination + " .t10-benchmark/translation-review.csv")
    }
} finally {
    Pop-Location
}
