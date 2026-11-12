$ErrorActionPreference = "Continue"
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$context = Join-Path $workspace "dashboard\backend"
$publisher = Join-Path $PSScriptRoot "publish-image.py"
$archive = Join-Path $env:TEMP ("crosslayer-dashboard-backend-" + [guid]::NewGuid().ToString("N") + ".tar")

try {
    & docker build -t crosslayer-dashboard-backend:latest $context
    if ($LASTEXITCODE -ne 0) { throw "Docker image build failed." }

    & docker save -o $archive crosslayer-dashboard-backend:latest
    if ($LASTEXITCODE -ne 0) { throw "Docker image export failed." }

    & python $publisher $archive
    if ($LASTEXITCODE -ne 0) { throw "Publishing the image to the MicroK8s registry failed." }
}
finally {
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
}
