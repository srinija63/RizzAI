# Fetch Stitch screens via HTTP MCP (works when stitch-mcp tool fails on Windows).
# Requires: $env:STITCH_API_KEY

param(
  [string]$ProjectId = "17404370540113652731",
  [string]$ScreenId = "048c3380cc92497c9042574ba7528e95",
  [string]$ScreenSlug = "rizzai-abstract-logo",
  [string]$AssetName = "rizz-logo.png"
)

if (-not $env:STITCH_API_KEY) {
  Write-Error "Set STITCH_API_KEY first (from stitch.withgoogle.com/settings)"
  exit 1
}

$root = Join-Path $PSScriptRoot ".."
$outDir = Join-Path $root "stitch\rizzai-logo-screen\$ScreenSlug"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$bodyPath = Join-Path $env:TEMP "stitch-mcp-body.json"
@{
  jsonrpc = "2.0"
  id      = 1
  method  = "tools/call"
  params  = @{
    name      = "get_screen"
    arguments = @{ projectId = $ProjectId; screenId = $ScreenId }
  }
} | ConvertTo-Json -Depth 6 -Compress | Set-Content -Path $bodyPath -Encoding utf8 -NoNewline

$respPath = Join-Path $outDir "screen-meta.json"
curl.exe -sS -X POST "https://stitch.googleapis.com/mcp" `
  -H "Content-Type: application/json" `
  -H "X-Goog-Api-Key: $env:STITCH_API_KEY" `
  --data-binary "@$bodyPath" `
  -o $respPath

$meta = Get-Content $respPath -Raw | ConvertFrom-Json
$url = $meta.result.structuredContent.screenshot.downloadUrl
if (-not $url) { Write-Error "No screenshot URL in response"; exit 1 }

$pngPath = Join-Path $outDir "screen.png"
curl.exe -sL $url -o $pngPath
Copy-Item $pngPath (Join-Path $root "assets\$AssetName") -Force
Write-Host "Saved assets/$AssetName and $pngPath"
