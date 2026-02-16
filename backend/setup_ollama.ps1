# Ollama Setup Script for Windows
# Run this in PowerShell as Administrator

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Ollama Setup for College Newsletter" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
$ollamaInstaller = "$env:TEMP\OllamaSetup.exe"

# Step 1: Download Ollama
Write-Host "[Step 1] Downloading Ollama..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaInstaller -UseBasicParsing
    Write-Host "Downloaded Ollama installer" -ForegroundColor Green
} catch {
    Write-Host "Failed to download. Please download manually from: https://ollama.com/download" -ForegroundColor Red
    exit 1
}

# Step 2: Install Ollama
Write-Host ""
Write-Host "[Step 2] Installing Ollama (click through the installer)..." -ForegroundColor Yellow
Start-Process -FilePath $ollamaInstaller -Wait

# Step 3: Add to PATH
Write-Host ""
Write-Host "[Step 3] Adding Ollama to PATH..." -ForegroundColor Yellow
$ollamaPath = "$env:LOCALAPPDATA\Programs\Ollama"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$ollamaPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$ollamaPath", "User")
    Write-Host "Added Ollama to PATH" -ForegroundColor Green
}

# Step 4: Start Ollama
Write-Host ""
Write-Host "[Step 4] Starting Ollama..." -ForegroundColor Yellow
$env:Path = "$env:Path;$ollamaPath"
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep 5

# Step 5: Pull model
Write-Host ""
Write-Host "[Step 5] Downloading llama3.2 model (this may take 10-15 minutes)..." -ForegroundColor Yellow
Write-Host "Model size: ~2GB" -ForegroundColor Gray
ollama pull llama3.2

if ($LASTEXITCODE -eq 0) {
    Write-Host "Model downloaded successfully!" -ForegroundColor Green
} else {
    Write-Host "Failed to download model. Try running manually: ollama pull llama3.2" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ollama is running on: http://localhost:11434" -ForegroundColor Yellow
Write-Host "Model: llama3.2" -ForegroundColor Yellow
Write-Host ""
Write-Host "Test it:" -ForegroundColor Green
Write-Host '  ollama run llama3.2 "Hello, are you working?"' -ForegroundColor White
Write-Host ""
Write-Host "Backend is ready to use local AI!" -ForegroundColor Green
Write-Host ""

Pause
