# Download Stitch screen HTML + screenshot.

# Prereq: npx @_davideast/stitch-mcp init

#

# Examples:

#   .\scripts\fetch-stitch-assets.ps1 -ScreenSlug rizzai-abstract-logo -ScreenId 048c3380cc92497c9042574ba7528e95

#   .\scripts\fetch-stitch-assets.ps1 -ScreenSlug rizzai-vibrant-splash -ScreenId 4ce103cb2c2c4a209198af8b828a37d1



param(

  [string]$ProjectId = "17404370540113652731",

  [string]$ScreenId = "048c3380cc92497c9042574ba7528e95",

  [string]$ScreenSlug = "rizzai-abstract-logo"

)



$OutDir = Join-Path $PSScriptRoot "..\stitch\rizzai-logo-screen\$ScreenSlug"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null



$payloadPath = Join-Path $PSScriptRoot "..\stitch\tmp-fetch-payload.json"
@{ projectId = $ProjectId; screenId = $ScreenId } | ConvertTo-Json -Compress | Set-Content -Path $payloadPath -Encoding utf8 -NoNewline
$metaPath = Join-Path $OutDir "screen-meta.json"

Write-Host "Fetching $ScreenSlug ($ScreenId)..."
npx --yes @_davideast/stitch-mcp tool get_screen -f $payloadPath -o json | Set-Content -Path $metaPath -Encoding utf8



$meta = Get-Content $metaPath -Raw | ConvertFrom-Json

$htmlUrl = $meta.htmlCode.downloadUrl

$imgUrl  = $meta.screenshot.downloadUrl



if ($htmlUrl) {

  Write-Host "Downloading HTML..."

  curl.exe -sL $htmlUrl -o (Join-Path $OutDir "screen.html")

}

if ($imgUrl) {

  Write-Host "Downloading screenshot..."

  curl.exe -sL $imgUrl -o (Join-Path $OutDir "screen.png")

  # Copy logo/splash PNG into app assets when fetched

  $assetsDir = Join-Path $PSScriptRoot "..\assets"

  if ($ScreenSlug -eq "rizzai-abstract-logo") {

    Copy-Item (Join-Path $OutDir "screen.png") (Join-Path $assetsDir "rizz-logo.png") -Force

    Write-Host "Updated assets/rizz-logo.png"

  }

  if ($ScreenSlug -eq "rizzai-vibrant-splash") {

    Copy-Item (Join-Path $OutDir "screen.png") (Join-Path $assetsDir "rizz-splash-reference.png") -Force

    Write-Host "Updated assets/rizz-splash-reference.png"

  }

}



Write-Host "Done: $OutDir"


