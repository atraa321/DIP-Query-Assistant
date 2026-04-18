param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$entry = Join-Path $projectRoot "run_app.py"

Set-Location $projectRoot

& $PythonExe -m PyInstaller `
  --noconfirm `
  --clean `
  --noconsole `
  --onedir `
  --name DIPAssistant `
  --paths (Join-Path $projectRoot "src") `
  $entry

Write-Host "打包完成。输出目录：" (Join-Path $projectRoot "dist\\DIPAssistant")
