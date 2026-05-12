Write-Host "Starting Medical AI Scan Assistant Development Servers..." -ForegroundColor Cyan

# Add virtual environment scripts to PATH
$env:PATH = "$(Join-Path (Get-Location) '.venv\Scripts');$env:PATH"

# Run the development task defined in package.json
npm run dev
