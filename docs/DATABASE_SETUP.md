# Database Setup Guide

## Quick Start (Automated)

### Option 1: PowerShell Script (Recommended)

1. **Open PowerShell as Administrator**
   - Press `Win + X`
   - Select "Windows PowerShell (Admin)" or "Terminal (Admin)"

2. **Run the setup script:**
   ```powershell
   cd D:\newsletter\backend
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
   .\setup_db.ps1
   ```

3. **Wait for installation to complete** (10-15 minutes)

### Option 2: Batch Script

1. **Open Command Prompt as Administrator**
   - Press `Win + R`
   - Type `cmd`
   - Press `Ctrl + Shift + Enter`

2. **Run the setup script:**
   ```cmd
   cd D:\newsletter\backend
   setup_database.bat
   ```

---

## Manual Installation

If automated scripts fail, follow these manual steps:

### PostgreSQL Installation

1. **Download PostgreSQL 15**
   - Go to: https://www.postgresql.org/download/windows/
   - Download "PostgreSQL 15.x" installer

2. **Run Installer**
   - Password: `your_password`
   - Port: `5432`
   - Keep other defaults

3. **Add to PATH**
   ```
   C:\Program Files\PostgreSQL\15\bin
   ```

4. **Create Database**
   ```sql
   CREATE DATABASE newsletter;
   ```

### Redis Installation

1. **Download Redis**
   - Go to: https://github.com/microsoftarchive/redis/releases
   - Download: `Redis-x64-3.0.504.zip`

2. **Extract to:**
   ```
   C:\Redis
   ```

3. **Add to PATH:**
   ```
   C:\Redis
   ```

4. **Start Redis:**
   ```cmd
   redis-server
   ```

---

## Verify Installation

### Check PostgreSQL
```cmd
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "\l"
```

### Check Redis
```cmd
redis-cli ping
```
Should return: `PONG`

---

## Start the Backend

Once databases are installed:

```cmd
cd D:\newsletter\backend

# Create virtual environment (if not done)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

Server will be available at: **http://localhost:8000**

---

## Troubleshooting

### PostgreSQL Service Won't Start
```cmd
net start postgresql-x64-15
```

### Redis Connection Refused
Make sure Redis is running:
```cmd
redis-server --daemonize yes
```

### Database Connection Error
Check credentials in `.env` file:
```
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/newsletter
```

### Port Already in Use
Change ports in `.env`:
```
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5433/newsletter
```
