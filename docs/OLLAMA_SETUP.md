# Ollama Setup Guide (Local AI)

## What is Ollama?

Ollama lets you run AI models locally on your computer - no internet required after download!

**Model:** llama3.2 (2GB download)  
**Speed:** ~10-30 tokens/second (depending on your CPU/GPU)  
**Cost:** FREE (runs on your hardware)

---

## Installation

### Step 1: Download Ollama

**Automatic (PowerShell):**
```powershell
cd D:\newsletter\backend
.\setup_ollama.ps1
```

**Manual:**
1. Go to: https://ollama.com/download
2. Download "Ollama for Windows"
3. Run the installer

---

### Step 2: Start Ollama

**Option A: As a service (recommended)**
```powershell
# Ollama should start automatically after install
# Check if it's running:
ollama --version
```

**Option B: Manual start**
```powershell
ollama serve
```

---

### Step 3: Download the Model

```powershell
ollama pull llama3.2
```

This downloads ~2GB. Wait for completion.

**Verify installation:**
```powershell
ollama list
```

Should show:
```
NAME            ID              SIZE    MODIFIED
llama3.2:latest xxxxxx          2.0GB   5 minutes ago
```

---

### Step 4: Test It

```powershell
ollama run llama3.2 "Hello, are you working?"
```

Should respond with something like:
```
Hello! Yes, I'm working properly. How can I help you today?
```

---

## Integration with Backend

The backend is already configured to use Ollama:

```env
# .env file (already set)
USE_LOCAL_AI=true
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

---

## Usage

### Via Frontend
1. Open `frontend/index.html` in browser
2. Go to "AI Content Processor" section
3. Enter title and content
4. Click "Summarize" or "Generate Headline"

### Via API
```bash
curl -X POST http://localhost:8000/api/v1/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "title": "OpenAI releases GPT-5",
    "content": "OpenAI announced GPT-5 with 10x performance...",
    "category": "tech"
  }'
```

---

## Troubleshooting

### "Connection refused" error
**Problem:** Ollama is not running  
**Fix:**
```powershell
ollama serve
```

### "Model not found" error
**Problem:** llama3.2 not downloaded  
**Fix:**
```powershell
ollama pull llama3.2
```

### Very slow responses
**Problem:** Running on CPU instead of GPU  
**Fix:** 
- Normal for CPU: 10-30 seconds per request
- To use GPU: Install NVIDIA CUDA drivers

### Out of memory
**Problem:** Not enough RAM  
**Fix:** Close other applications or use smaller model:
```powershell
ollama pull llama3.2:1b  # Smaller 1B parameter version
```

---

## Performance Tips

| Hardware | Expected Speed |
|----------|----------------|
| CPU only | 10-30 sec/request |
| NVIDIA GPU | 2-5 sec/request |
| Apple Silicon | 3-8 sec/request |

**To speed up:**
1. Use NVIDIA GPU with CUDA
2. Close other applications
3. Use smaller model (llama3.2:1b)

---

## Alternative Models

If llama3.2 doesn't work, try these:

```powershell
# Smaller, faster
ollama pull llama3.2:1b

# More capable (but slower)
ollama pull llama3.1

# Code-focused
ollama pull codellama
```

Update `.env`:
```env
OLLAMA_MODEL=llama3.2:1b
```

---

## Status Check

```bash
# Check Ollama status
http://localhost:8000/api/v1/ai/status

# Should return:
{
  "status": "ready",
  "message": "Ollama is ready with model: llama3.2",
  "models_available": ["llama3.2:latest"]
}
```

---

## Next Steps

Once Ollama is running:
1. ✅ Backend automatically uses it
2. ✅ Frontend can call AI endpoints
3. ✅ Content gets summarized locally
4. ✅ Headlines generated locally

No API keys needed! Everything runs on your machine.
