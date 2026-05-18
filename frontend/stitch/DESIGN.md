# Stitch references — RizzAI Logo Screen

**Project ID:** `17404370540113652731`

```powershell
cd frontend
$env:STITCH_API_KEY = "your-key-from-stitch.withgoogle.com/settings"

# Recommended on Windows (HTTP API):
.\scripts\fetch-stitch-via-api.ps1 -ScreenId 048c3380cc92497c9042574ba7528e95 -ScreenSlug rizzai-abstract-logo -AssetName rizz-logo.png
.\scripts\fetch-stitch-via-api.ps1 -ScreenId 4ce103cb2c2c4a209198af8b828a37d1 -ScreenSlug rizzai-vibrant-splash -AssetName rizz-splash-reference.png
```

| Screen | ID | App asset / screen |
|--------|-----|-------------------|
| rizzAI Abstract Logo | `048c3380cc92497c9042574ba7528e95` | `assets/rizz-logo.png`, `RizzWireframeHeartIcon` |
| rizzAI Vibrant Splash Screen | `4ce103cb2c2c4a209198af8b828a37d1` | `HeroIntroScreen`, `animated-shader-hero` |

Until Stitch auth is set up, `assets/rizz-logo.png` is cropped from `rizz-splash-reference.png`.
