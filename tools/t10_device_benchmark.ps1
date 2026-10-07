param(
    [Parameter(Mandatory = $true)]
    [string]$DatasetManifest,

    [string]$WorkDir = ".t10-benchmark",
    [string]$DeviceSerial = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WorkDir = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $WorkDir))
$ManifestPath = [System.IO.Path]::GetFullPath($DatasetManifest)
$Sdk = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } elseif ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android\Sdk" }
$Adb = Join-Path $Sdk "platform-tools\adb.exe"
$NdkVersion = "28.2.13676358"
$CmakeVersion = "3.22.1"
$Remote = "/data/local/tmp/subloka-t10"
$ModelRevision = "80da2d8bfee42b0e836fc3a9890373e5defc00a6"

if (!(Test-Path $ManifestPath)) {
    throw "Dataset manifest tidak ditemukan: $ManifestPath. Path pada contoh hanyalah placeholder; gunakan path JSON dataset nyata."
}
if (!(Test-Path $Adb)) {
    throw "adb.exe tidak ditemukan: $Adb. Pastikan Android SDK Platform-Tools terpasang."
}

$Dataset = Get-Content $ManifestPath -Raw | ConvertFrom-Json
if (!$Dataset.samples) { throw "Manifest harus memiliki array samples." }

$AllowedLanguages = @("en", "id")
$AllowedCategories = @("clean", "challenging")
$SeenIds = @{}

foreach ($Sample in $Dataset.samples) {
    if (!$Sample.id -or $SeenIds.ContainsKey([string]$Sample.id)) {
        throw "Setiap sample harus memiliki id unik. Duplikat/kosong: $($Sample.id)"
    }
    $SeenIds[[string]$Sample.id] = $true

    if ($AllowedLanguages -notcontains [string]$Sample.language) {
        throw "Language sample $($Sample.id) harus en atau id."
    }
    if ($AllowedCategories -notcontains [string]$Sample.category) {
        throw "Category sample $($Sample.id) harus clean atau challenging."
    }

    $Reference = [string]$Sample.reference
    if ([string]::IsNullOrWhiteSpace($Reference) -or $Reference -match "^__FILL_" -or $Reference -match "Replace with|Ganti dengan") {
        throw "Reference transcript belum diisi/review untuk sample $($Sample.id)."
    }

    $Duration = [double]$Sample.durationSeconds
    if ($Duration -le 0) {
        throw "durationSeconds belum valid untuk sample $($Sample.id)."
    }

    $AudioPath = [System.IO.Path]::GetFullPath((Join-Path (Split-Path $ManifestPath) ([string]$Sample.audio)))
    if (!(Test-Path $AudioPath)) {
        throw "Audio sample tidak ditemukan untuk $($Sample.id): $AudioPath"
    }
}

foreach ($Lang in $AllowedLanguages) {
    $Clean = @($Dataset.samples | Where-Object { $_.language -eq $Lang -and $_.category -eq "clean" }).Count
    $Challenging = @($Dataset.samples | Where-Object { $_.language -eq $Lang -and $_.category -eq "challenging" }).Count
    if ($Clean -lt 20 -or $Challenging -lt 10) {
        throw "Dataset $Lang belum memenuhi gate 20 clean + 10 challenging. Saat ini clean=$Clean challenging=$Challenging"
    }
}

Write-Host "Dataset preflight PASS: $($Dataset.samples.Count) samples."

$Cmake = Join-Path $Sdk "cmake\$CmakeVersion\bin\cmake.exe"
$Ninja = Join-Path $Sdk "cmake\$CmakeVersion\bin\ninja.exe"
$Toolchain = Join-Path $Sdk "ndk\$NdkVersion\build\cmake\android.toolchain.cmake"

function Find-SdkManager {
    $CommandLineTools = Join-Path $Sdk "cmdline-tools"
    if (!(Test-Path $CommandLineTools)) { return $null }

    return Get-ChildItem -Path $CommandLineTools -Filter "sdkmanager.bat" -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

$NeedNativeToolchain = !(Test-Path $Cmake) -or !(Test-Path $Ninja) -or !(Test-Path $Toolchain)
if ($NeedNativeToolchain) {
    $SdkManager = Find-SdkManager
    if (!$SdkManager) {
        throw @"
Android SDK Command-line Tools belum ditemukan di:
$Sdk\cmdline-tools

NDK $NdkVersion atau CMake $CmakeVersion juga belum lengkap.
Buka Android Studio > Settings > Languages & Frameworks > Android SDK > SDK Tools,
centang "Android SDK Command-line Tools (latest)", lalu Apply.
Setelah itu jalankan script ini lagi.
"@
    }

    Write-Host "Menggunakan sdkmanager: $SdkManager"
    & $SdkManager "ndk;$NdkVersion" "cmake;$CmakeVersion" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Instalasi NDK/CMake melalui sdkmanager gagal." }
}

foreach ($RequiredTool in @($Cmake, $Ninja, $Toolchain)) {
    if (!(Test-Path $RequiredTool)) {
        throw "Native toolchain belum lengkap setelah setup: $RequiredTool"
    }
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

$SourceArchive = Join-Path $WorkDir "whisper-v1.9.4.tar.gz"
$SourceDir = Join-Path $WorkDir "whisper.cpp-1.9.4"
$BuildDir = Join-Path $WorkDir "build-android"
if (!(Test-Path $SourceDir)) {
    curl.exe -L --fail --retry 3 -o $SourceArchive "https://github.com/ggml-org/whisper.cpp/archive/refs/tags/v1.9.4.tar.gz"
    tar.exe -xzf $SourceArchive -C $WorkDir
}

& $Cmake -S $SourceDir -B $BuildDir -G Ninja `
    "-DCMAKE_MAKE_PROGRAM=$Ninja" `
    "-DCMAKE_TOOLCHAIN_FILE=$Toolchain" `
    "-DANDROID_ABI=arm64-v8a" `
    "-DANDROID_PLATFORM=android-26" `
    "-DANDROID_STL=c++_static" `
    "-DCMAKE_BUILD_TYPE=Release" `
    "-DWHISPER_BUILD_TESTS=OFF" `
    "-DWHISPER_BUILD_EXAMPLES=ON" `
    "-DGGML_OPENMP=OFF" `
    "-DGGML_NATIVE=OFF"
if ($LASTEXITCODE -ne 0) { throw "CMake configure gagal." }
& $Cmake --build $BuildDir --target whisper-cli -j 2
if ($LASTEXITCODE -ne 0) { throw "Build whisper-cli Android gagal." }

$Cli = Join-Path $BuildDir "bin\whisper-cli"
if (!(Test-Path $Cli)) { throw "whisper-cli tidak ditemukan: $Cli" }

$Models = @(
    @{ Name = "tiny"; File = "ggml-tiny.bin"; Sha = "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21" },
    @{ Name = "base"; File = "ggml-base.bin"; Sha = "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe" }
)
$ModelDir = Join-Path $WorkDir "models"
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
foreach ($Model in $Models) {
    $Path = Join-Path $ModelDir $Model.File
    if (!(Test-Path $Path) -or ((Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Model.Sha)) {
        curl.exe -L --fail --retry 3 -o $Path "https://huggingface.co/ggerganov/whisper.cpp/resolve/$ModelRevision/$($Model.File)?download=true"
    }
    $Actual = (Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $Model.Sha) { throw "Checksum model $($Model.Name) tidak cocok." }
}

$AdbArgs = @()
if ($DeviceSerial) { $AdbArgs += @("-s", $DeviceSerial) }
function Invoke-Adb([string[]]$Arguments) {
    & $Adb @AdbArgs @Arguments
    if ($LASTEXITCODE -ne 0) { throw "ADB gagal: $($Arguments -join ' ')" }
}

Invoke-Adb @("wait-for-device")
$Abi = (& $Adb @AdbArgs shell getprop ro.product.cpu.abi).Trim()
if ($Abi -ne "arm64-v8a") { throw "Benchmark binary membutuhkan arm64-v8a, device melaporkan $Abi" }
Invoke-Adb @("shell", "mkdir -p $Remote")
Invoke-Adb @("push", $Cli, "$Remote/whisper-cli")
Invoke-Adb @("shell", "chmod 755 $Remote/whisper-cli")

$DeviceInfo = [ordered]@{
    manufacturer = (& $Adb @AdbArgs shell getprop ro.product.manufacturer).Trim()
    model = (& $Adb @AdbArgs shell getprop ro.product.model).Trim()
    android = (& $Adb @AdbArgs shell getprop ro.build.version.release).Trim()
    sdk = (& $Adb @AdbArgs shell getprop ro.build.version.sdk).Trim()
    abi = $Abi
    meminfo = ((& $Adb @AdbArgs shell "grep MemTotal /proc/meminfo") -join " ").Trim()
}
$DeviceInfo | ConvertTo-Json | Set-Content (Join-Path $WorkDir "device.json") -Encoding UTF8

function Get-Wer([string]$Reference, [string]$Hypothesis) {
    $RefFile = Join-Path $WorkDir "_ref.txt"
    $HypFile = Join-Path $WorkDir "_hyp.txt"
    Set-Content $RefFile $Reference -Encoding UTF8
    Set-Content $HypFile $Hypothesis -Encoding UTF8
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if (!$Python) { throw "Python diperlukan untuk tools/t10_wer.py." }
    $Value = & python (Join-Path $RepoRoot "tools\t10_wer.py") $RefFile $HypFile
    if ($LASTEXITCODE -ne 0) { throw "Perhitungan WER gagal." }
    return [double]$Value
}

$Results = @()
foreach ($Model in $Models) {
    $LocalModel = Join-Path $ModelDir $Model.File
    Invoke-Adb @("push", $LocalModel, "$Remote/model.bin")

    foreach ($Sample in $Dataset.samples) {
        $Audio = [System.IO.Path]::GetFullPath((Join-Path (Split-Path $ManifestPath) $Sample.audio))
        if (!(Test-Path $Audio)) { throw "Audio tidak ditemukan: $Audio" }
        if ([double]$Sample.durationSeconds -le 0) { throw "durationSeconds invalid untuk $($Sample.id)" }

        Invoke-Adb @("push", $Audio, "$Remote/input.wav")
        $Stdout = Join-Path $WorkDir "_stdout.txt"
        $Stderr = Join-Path $WorkDir "_stderr.txt"
        Remove-Item $Stdout,$Stderr -Force -ErrorAction SilentlyContinue

        $AdbProcessArgs = @($AdbArgs + @("shell", "cd $Remote && ./whisper-cli -m model.bin -f input.wav -l $($Sample.language) -nt"))
        $Watch = [System.Diagnostics.Stopwatch]::StartNew()
        $Process = Start-Process -FilePath $Adb -ArgumentList $AdbProcessArgs -NoNewWindow -PassThru -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr
        $PeakRssKb = 0
        while (!$Process.HasExited) {
            $PidText = (& $Adb @AdbArgs shell "pidof whisper-cli" 2>$null).Trim()
            if ($PidText) {
                $RemotePid = ($PidText -split "\s+")[0]
                $RssLine = (& $Adb @AdbArgs shell "grep VmRSS /proc/$RemotePid/status" 2>$null) -join " "
                if ($RssLine -match "(\d+)\s+kB") {
                    $PeakRssKb = [Math]::Max($PeakRssKb, [int]$Matches[1])
                }
            }
            Start-Sleep -Milliseconds 200
        }
        $Process.WaitForExit()
        $Watch.Stop()
        if ($Process.ExitCode -ne 0) {
            throw "whisper-cli gagal untuk $($Model.Name)/$($Sample.id): $(Get-Content $Stderr -Raw)"
        }

        $Hypothesis = (Get-Content $Stdout -Raw).Trim()
        if (!$Hypothesis) { throw "Transkripsi kosong untuk $($Model.Name)/$($Sample.id)" }
        $Wer = Get-Wer ([string]$Sample.reference) $Hypothesis
        $ElapsedSec = $Watch.Elapsed.TotalSeconds
        $Rtf = $ElapsedSec / [double]$Sample.durationSeconds
        $Results += [pscustomobject]@{
            model = $Model.Name
            sample = $Sample.id
            language = $Sample.language
            category = $Sample.category
            duration_s = [double]$Sample.durationSeconds
            elapsed_s = [Math]::Round($ElapsedSec, 3)
            rtf = [Math]::Round($Rtf, 4)
            peak_rss_kb = $PeakRssKb
            wer = [Math]::Round($Wer, 4)
            hypothesis = $Hypothesis
        }
    }
}

$ResultCsv = Join-Path $WorkDir "asr-results.csv"
$Results | Export-Csv $ResultCsv -NoTypeInformation -Encoding UTF8
$Summary = $Results | Group-Object model,language,category | ForEach-Object {
    $Rows = $_.Group
    [pscustomobject]@{
        group = $_.Name
        samples = $Rows.Count
        mean_wer = [Math]::Round((($Rows | Measure-Object wer -Average).Average), 4)
        mean_rtf = [Math]::Round((($Rows | Measure-Object rtf -Average).Average), 4)
        max_rss_kb = ($Rows | Measure-Object peak_rss_kb -Maximum).Maximum
    }
}
$Summary | Export-Csv (Join-Path $WorkDir "asr-summary.csv") -NoTypeInformation -Encoding UTF8
$Summary | Format-Table -AutoSize | Out-Host
Write-Host "Hasil tersimpan di $WorkDir"
