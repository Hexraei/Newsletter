# College Newsletter Database Setup Script
# Run as Administrator

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "College Newsletter - Database Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "Error: Please run this script as Administrator" -ForegroundColor Red
    Write-Host "Right-click on PowerShell and select 'Run as administrator'" -ForegroundColor Yellow
    exit 1
}

# PostgreSQL Configuration
$pgVersion = "15"
$pgPassword = "your_password"
$dbName = "newsletter"
$pgPath = "C:\Program Files\PostgreSQL\$pgVersion"

Write-Host "[Step 1] Downloading PostgreSQL $pgVersion..." -ForegroundColor Yellow

# Download PostgreSQL installer
$pgUrl = "https://get.enterprisedb.com/postgresql/postgresql-$pgVersion.4-1-windows-x64.exe"
$pgInstaller = "$env:TEMP\postgresql-installer.exe"

try {
    Invoke-WebRequest -Uri $pgUrl -OutFile $pgInstaller -UseBasicParsing
    Write-Host "Downloaded PostgreSQL installer" -ForegroundColor Green
} catch {
    Write-Host "Failed to download PostgreSQL. Trying alternative method..." -ForegroundColor Red
    Write-Host "Please download and install manually from: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
}

if (Test-Path $pgInstaller) {
    Write-Host "[Step 2] Installing PostgreSQL (this may take a few minutes)..." -ForegroundColor Yellow
    
    # Silent install
    $pgArgs = @(
        "--mode unattended"
        "--unattendedmodeui minimal"
        "--serverport 5432"
        "--superpassword $pgPassword"
        "--enable_acledit 1"
    ) -join " "
    
    Start-Process -FilePath $pgInstaller -ArgumentList $pgArgs -Wait
    Write-Host "PostgreSQL installation completed" -ForegroundColor Green
}

# Check if PostgreSQL is installed
if (Test-Path $pgPath) {
    Write-Host "[Step 3] Configuring PostgreSQL..." -ForegroundColor Yellow
    
    # Add to PATH
    $pgBin = "$pgPath\bin"
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($currentPath -notlike "*$pgBin*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$pgBin", "Machine")
        $env:Path = "$env:Path;$pgBin"
        Write-Host "Added PostgreSQL to PATH" -ForegroundColor Green
    }
    
    # Start service
    $serviceName = "postgresql-x64-$pgVersion"
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    
    if ($service) {
        if ($service.Status -ne "Running") {
            Start-Service $serviceName
            Write-Host "Started PostgreSQL service" -ForegroundColor Green
        } else {
            Write-Host "PostgreSQL service already running" -ForegroundColor Green
        }
    } else {
        Write-Host "PostgreSQL service not found. Please check installation." -ForegroundColor Red
    }
    
    # Create database
    Write-Host "[Step 4] Creating database '$dbName'..." -ForegroundColor Yellow
    
    $env:PGPASSWORD = $pgPassword
    & "$pgBin\createdb.exe" -U postgres $dbName 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Database '$dbName' created successfully" -ForegroundColor Green
    } else {
        Write-Host "Database may already exist or creation failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "PostgreSQL installation directory not found at $pgPath" -ForegroundColor Red
}

# Redis Installation
Write-Host ""
Write-Host "[Step 5] Downloading Redis..." -ForegroundColor Yellow

$redisUrl = "https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip"
$redisZip = "$env:TEMP\redis.zip"
$redisPath = "C:\Redis"

try {
    Invoke-WebRequest -Uri $redisUrl -OutFile $redisZip -UseBasicParsing
    Write-Host "Downloaded Redis" -ForegroundColor Green
    
    # Extract
    Expand-Archive -Path $redisZip -DestinationPath $redisPath -Force
    Write-Host "Extracted Redis to $redisPath" -ForegroundColor Green
    
    # Add to PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($currentPath -notlike "*$redisPath*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$redisPath", "Machine")
        $env:Path = "$env:Path;$redisPath"
        Write-Host "Added Redis to PATH" -ForegroundColor Green
    }
    
    # Start Redis
    Start-Process -FilePath "$redisPath\redis-server.exe" -ArgumentList "--daemonize yes" -WindowStyle Hidden
    Write-Host "Started Redis server" -ForegroundColor Green
    
} catch {
    Write-Host "Failed to install Redis: $_" -ForegroundColor Red
    Write-Host "You can install Redis manually from: https://github.com/microsoftarchive/redis/releases" -ForegroundColor Yellow
}

# Create .env file
Write-Host ""
Write-Host "[Step 6] Creating .env file..." -ForegroundColor Yellow

$envContent = @"
# App
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:$pgPassword@localhost:5432/$dbName

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# Email
FROM_EMAIL=newsletter@example.com
"@

$envContent | Out-File -FilePath ".env" -Encoding utf8
Write-Host "Created .env file with database configuration" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PostgreSQL:" -ForegroundColor Yellow
Write-Host "  Host: localhost:5432" -ForegroundColor White
Write-Host "  Database: $dbName" -ForegroundColor White
Write-Host "  Username: postgres" -ForegroundColor White
Write-Host "  Password: $pgPassword" -ForegroundColor White
Write-Host ""
Write-Host "Redis:" -ForegroundColor Yellow
Write-Host "  Host: localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "  1. Run: .\venv\Scripts\activate" -ForegroundColor White
Write-Host "  2. Run: alembic upgrade head" -ForegroundColor White
Write-Host "  3. Run: uvicorn app.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan

Pause
