# Groq Setup (RECOMMENDED - FREE & Fast!)

## Why Groq?

✅ **FREE tier** - 20 requests/minute, 1M tokens/day  
✅ **Extremely fast** - 500+ tokens/second  
✅ **No installation** - Just an API key  
✅ **Uses Llama 3.2** - Same quality as Ollama

---

## Setup (3 Minutes)

### Step 1: Sign Up (1 minute)

1. Go to https://console.groq.com/
2. Click **"Sign In"** (top right)
3. Sign up with:
   - Google account, OR
   - Email + password
4. Verify your email (check inbox)

### Step 2: Get API Key (1 minute)

1. In Groq console, click **"API Keys"** (left sidebar)
2. Click **"Create API Key"**
3. Name it: `newsletter-app`
4. Copy the key (starts with `gsk_`)

### Step 3: Configure Backend (1 minute)

Edit `backend/.env`:
```env
# Add this line
GROQ_API_KEY=gsk_your_actual_key_here
```

**That's it!** No other changes needed.

---

## Test It

```bash
cd D:\newsletter\backend
python test_ai_system.py
```

Should show:
```
✓ ALL TESTS PASSED! AI SYSTEM IS WORKING
```

---

## Usage in Frontend

1. Open `frontend/index.html`
2. Go to "AI Content Processor"
3. Enter any news article
4. Click "Summarize"
5. **Response in 1-2 seconds!** ⚡

---

## Free Tier Limits

| Metric | Limit |
|--------|-------|
| Requests/minute | 20 |
| Tokens/day | 1,000,000 |
| Models | Llama 3.2, Mixtral, Gemma |

**For testing:** More than enough  
**For production:** Upgrade when needed

---

## Compare Options

| Feature | Groq | OpenAI | Ollama |
|---------|------|--------|--------|
| **Setup** | 3 min | 5 min | 15 min |
| **Cost** | FREE | $5-20/mo | FREE |
| **Speed** | ⚡ Very Fast | Fast | Slow |
| **Quality** | Good | Best | Good |
| **Offline** | ❌ No | ❌ No | ✅ Yes |

---

## Troubleshooting

### "Invalid API key"
- Make sure you copied the full key (starts with `gsk_`)
- Key should be 56 characters long

### "Rate limit exceeded"
- You're making too many requests
- Wait a minute and try again
- Or upgrade to paid tier

### "Model not found"
- Groq updates models regularly
- The code uses `llama-3.2-3b-preview` which should work

---

## Need More?

Groq paid plans:
- **Starter**: $5/month
- **Pro**: $25/month

See: https://console.groq.com/settings/billing

---

## Summary

**Groq is the best option because:**
1. ✅ Free tier is generous
2. ✅ Setup takes 3 minutes
3. ✅ No software to install
4. ✅ Extremely fast responses
5. ✅ Good enough quality

**Get your API key now:** https://console.groq.com/
