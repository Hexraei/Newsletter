# OpenAI Setup (5 Minutes - No Installation!)

## Option 1: OpenAI (Recommended - Easiest)

### Step 1: Get API Key (2 minutes)

1. Go to https://platform.openai.com/
2. Sign up with your email or Google account
3. Verify your email
4. Go to **"API Keys"** in the left sidebar
5. Click **"Create new secret key"**
6. Copy the key (starts with `sk-`)

### Step 2: Add to Environment (1 minute)

Edit `backend/.env`:
```env
OPENAI_API_KEY=sk-your-actual-key-here
USE_LOCAL_AI=false
```

### Step 3: Test (2 minutes)

```bash
cd D:\newsletter\backend
python test_ai_system.py
```

Should show **"ALL TESTS PASSED!"**

---

## Cost

| Usage | Cost |
|-------|------|
| Summarization | ~$0.002 per article |
| Headlines | ~$0.001 per headline |
| Free trial | $5 credit for new accounts |

**Realistic usage:** $2-5 per month for testing

---

## Alternative: Free AI Options

### Option 2: Groq (FREE tier - Very fast!)

1. Go to https://console.groq.com/
2. Sign up (free)
3. Get API key
4. I'll update the code to use Groq

### Option 3: Together AI (FREE credits)

1. Go to https://www.together.ai/
2. Sign up ($5 free credit)
3. Use open-source models for free

### Option 4: Ollama (100% FREE)

Install locally - no API needed. See `OLLAMA_SETUP.md`

---

## Quick Test

Once you add the API key, test the AI:

```bash
# Start backend
uvicorn app.main:app --reload

# In another terminal
curl -X POST http://localhost:8000/api/v1/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "title": "OpenAI releases GPT-5",
    "content": "OpenAI announced GPT-5 with 10x performance improvement over GPT-4..."
  }'
```

Response in 2-3 seconds!

---

## Which Should You Choose?

| Option | Setup Time | Cost | Speed | Quality |
|--------|------------|------|-------|---------|
| **OpenAI** | 5 min | $2-5/mo | Fast | Best |
| **Groq** | 5 min | FREE | Very Fast | Good |
| **Ollama** | 15 min | FREE | Slow | Good |

---

## Need Help?

If you want me to:
- ✅ Integrate Groq instead (faster, free tier)
- ✅ Integrate Together AI
- ✅ Keep Ollama as backup

Just say the word!
