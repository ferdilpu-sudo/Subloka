param(
    [string]$ManifestPath = "t10-dataset.json",
    [string]$AudioDirectory = "t10-audio"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ManifestFullPath = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $ManifestPath))
$AudioFullPath = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $AudioDirectory))

if (Test-Path $ManifestFullPath) {
    throw "Manifest sudah ada: $ManifestFullPath. Script tidak akan menimpa data yang mungkin sudah kamu isi."
}

New-Item -ItemType Directory -Force -Path $AudioFullPath | Out-Null
foreach ($Subdir in @("en-clean", "en-challenging", "id-clean", "id-challenging")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $AudioFullPath $Subdir) | Out-Null
}

$Samples = @()
function Add-Samples([string]$Language, [string]$Category, [int]$Count) {
    for ($Index = 1; $Index -le $Count; $Index++) {
        $Number = "{0:D2}" -f $Index
        $Id = "$Language-$Category-$Number"
        $RelativeAudio = "$AudioDirectory/$Language-$Category/$Id.wav".Replace("\\", "/")
        $script:Samples += [ordered]@{
            id = $Id
            language = $Language
            category = $Category
            audio = $RelativeAudio
            reference = "__FILL_REVIEWED_TRANSCRIPT__"
            durationSeconds = 0
        }
    }
}

Add-Samples "en" "clean" 20
Add-Samples "en" "challenging" 10
Add-Samples "id" "clean" 20
Add-Samples "id" "challenging" 10

$Manifest = [ordered]@{
    version = 1
    note = "CP4 dataset manusia. Isi file WAV, transcript acuan yang sudah ditinjau, dan durationSeconds aktual. Placeholder sengaja ditolak benchmark."
    samples = $Samples
}

$Manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestFullPath -Encoding UTF8

Write-Host "Dataset scaffold dibuat:"
Write-Host "  Manifest : $ManifestFullPath"
Write-Host "  Audio    : $AudioFullPath"
Write-Host "  Samples  : $($Samples.Count)"
Write-Host ""
Write-Host "Berikutnya:"
Write-Host "1. Rekam/siapkan file WAV manusia sesuai nama pada manifest."
Write-Host "2. Ganti __FILL_REVIEWED_TRANSCRIPT__ dengan transkrip acuan yang sudah ditinjau."
Write-Host "3. Isi durationSeconds aktual > 0."
Write-Host "4. Jalankan tools\t10_device_benchmark.ps1 dengan manifest ini."
