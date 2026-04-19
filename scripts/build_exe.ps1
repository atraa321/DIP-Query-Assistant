param(
    [string]$PythonExe = "py",
    [string[]]$PythonArgs = @("-3.8")
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$entry = Join-Path $projectRoot "run_app.py"
$distRoot = Join-Path $projectRoot "dist"
$buildRoot = Join-Path $projectRoot "build"
$outputDir = Join-Path $distRoot "DIPAssistant"
$configDir = Join-Path $projectRoot "config"
$dataDir = Join-Path $projectRoot "data"
$sourceDir = Join-Path $projectRoot "数据源"
$buildScript = Join-Path $projectRoot "scripts\\build_data.py"
$iconPath = Join-Path $projectRoot "assets\\app-icon.ico"
$versionFilePath = Join-Path $projectRoot "build_version_info.txt"
$releaseConfigDir = Join-Path $outputDir "config"
$releaseDataDir = Join-Path $outputDir "data"
$releaseSourceDir = Join-Path $outputDir "数据源"
$releaseSettingsPath = Join-Path $releaseConfigDir "settings.json"
$tempSettingsPath = Join-Path $configDir "settings.release.json"
$win7IncompatibleRuntimePatterns = @(
  "api-ms-win-*",
  "ucrtbase.dll"
)

Set-Location $projectRoot

if (Test-Path $tempSettingsPath) {
  Remove-Item -LiteralPath $tempSettingsPath -Force
}

Get-Process -Name "DIPAssistant" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

& $PythonExe @PythonArgs $buildScript
if ($LASTEXITCODE -ne 0) {
  throw "重建查询库失败。"
}

if (Test-Path $outputDir) {
  Remove-Item -LiteralPath $outputDir -Recurse -Force
}

& $PythonExe @PythonArgs -m PyInstaller `
  --noconfirm `
  --clean `
  --noconsole `
  --onedir `
  --name DIPAssistant `
  --icon $iconPath `
  --version-file $versionFilePath `
  --paths (Join-Path $projectRoot "src") `
  $entry
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller 打包失败。"
}

New-Item -ItemType Directory -Force -Path $releaseConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $releaseDataDir | Out-Null
New-Item -ItemType Directory -Force -Path $releaseSourceDir | Out-Null

if (Test-Path $iconPath) {
  Copy-Item -LiteralPath $iconPath -Destination (Join-Path $outputDir "app-icon.ico") -Force
}

if (Test-Path (Join-Path $configDir "settings.example.json")) {
  Copy-Item -LiteralPath (Join-Path $configDir "settings.example.json") -Destination (Join-Path $releaseConfigDir "settings.example.json") -Force
}

if (Test-Path (Join-Path $configDir "settings.json")) {
  $config = Get-Content -Raw (Join-Path $configDir "settings.json") | ConvertFrom-Json
} else {
  $config = [pscustomobject]@{
    resident_point_value = $null
    employee_point_value = $null
    window_x = 200
    window_y = 80
    window_width = 540
    window_height = 480
    always_on_top = $true
    idle_opacity = 0.78
  }
}

$releaseConfig = [ordered]@{
  resident_point_value = $config.resident_point_value
  employee_point_value = $config.employee_point_value
  database_path = "data\\dip_lookup.db"
  source_directory = "数据源"
  window_x = $config.window_x
  window_y = $config.window_y
  window_width = $config.window_width
  window_height = $config.window_height
  always_on_top = $config.always_on_top
  idle_opacity = $config.idle_opacity
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$writer = New-Object System.IO.StreamWriter($releaseSettingsPath, $false, $utf8NoBom)
try {
  $writer.Write(($releaseConfig | ConvertTo-Json -Depth 3))
} finally {
  $writer.Dispose()
}

if (Test-Path (Join-Path $dataDir "dip_lookup.db")) {
  Copy-Item -LiteralPath (Join-Path $dataDir "dip_lookup.db") -Destination (Join-Path $releaseDataDir "dip_lookup.db") -Force
}

if (Test-Path $sourceDir) {
  Copy-Item -LiteralPath (Join-Path $sourceDir "*") -Destination $releaseSourceDir -Recurse -Force
}

foreach ($pattern in $win7IncompatibleRuntimePatterns) {
  Get-ChildItem -Path $outputDir -Filter $pattern -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
  }
}

Write-Host "打包完成。输出目录：" $outputDir
