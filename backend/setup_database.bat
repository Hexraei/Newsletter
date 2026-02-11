@echo off
chcp 65001 >nul
echo ============================================
echo College Newsletter - Database Setup
echo ============================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Error: Please run this script as Administrator
    echo Right-click on the script and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/4] Checking for Chocolatey package manager...
where choco >nul 2>&1
if %errorLevel% neq 0 (
    echo Installing Chocolatey...
    @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
    echo Chocolatey installed successfully!
) else (
    echo Chocolatey already installed.
)

echo.
echo [2/4] Installing PostgreSQL 15...
choco install postgresql15 --params '/Password:newsletter123' -y
if %errorLevel% neq 0 (
    echo Failed to install PostgreSQL. Retrying...
    timeout /t 5 /nobreak >nul
    choco install postgresql15 --params '/Password:newsletter123' -y --force
)

echo.
echo [3/4] Installing Redis...
choco install redis-64 -y
if %errorLevel% neq 0 (
    echo Failed to install Redis. Retrying...
    timeout /t 5 /nobreak >nul
    choco install redis-64 -y --force
)

echo.
echo [4/4] Setting up environment variables...
SET "PATH=%PATH%;C:\Program Files\PostgreSQL\15\bin"
SETX PATH "%PATH%;C:\Program Files\PostgreSQL\15\bin" /M

echo.
echo ============================================
echo Installation Complete!
echo ============================================
echo.
echo Starting services...

:: Start PostgreSQL
net start postgresql-x64-15
if %errorLevel% neq 0 (
    echo Note: PostgreSQL service may need to be started manually
    echo Run: net start postgresql-x64-15
)

:: Start Redis
redis-server --service-install
redis-server --service-start
if %errorLevel% neq 0 (
    echo Starting Redis in background mode...
    start /B redis-server
)

echo.
echo Creating database 'newsletter'...
set PGUSER=postgres
set PGPASSWORD=newsletter123
"C:\Program Files\PostgreSQL\15\bin\createdb.exe" -U postgres newsletter 2>nul
if %errorLevel% neq 0 (
    echo Database may already exist or needs manual creation
    echo To create manually, run:
    echo   "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE newsletter;"
)

echo.
echo ============================================
echo Setup Summary
echo ============================================
echo PostgreSQL: localhost:5432
echo   Database: newsletter
echo   Username: postgres
echo   Password: newsletter123
echo.
echo Redis: localhost:6379
echo.
echo Next steps:
echo 1. Update .env file with these credentials
echo 2. Run: alembic upgrade head
echo 3. Run: uvicorn app.main:app --reload
echo.
pause
