# 🚀 Ollama Setup Guide (Local, Free LLM)

## ✅ Why Ollama?

- ✅ **100% FREE** - No API keys, no billing
- ✅ **100% LOCAL** - Runs on your machine
- ✅ **100% OFFLINE** - Works without internet
- ✅ **NO RATE LIMITS** - Process unlimited videos
- ✅ **PRIVATE** - Your data never leaves your machine

---

## 🎯 Quick Setup

### Step 1: Install Ollama

**Windows:**
1. Download from: https://ollama.com/download
2. Run the installer
3. Ollama will start automatically

**Verify:**
```powershell
ollama --version
```

You should see a version number.

### Step 2: Pull a Model

```powershell
ollama pull gemma2:2b
```

This downloads a small, fast model perfect for MCQ generation (~2GB).

**Alternative models (better quality, larger):**
```powershell
ollama pull llama3        # ~4.7GB - Better quality
ollama pull mistral      # ~4.1GB - Good balance
```

### Step 3: Verify Ollama is Running

Open browser: http://localhost:11434

You should see: **"Ollama is running"**

### Step 4: Run Your Script!

```powershell
python youtube_quiz_generator.py "https://youtu.be/VIDEO_ID"
```

The script will automatically detect Ollama and use it! 🎉

---

## 🎯 Your Complete FREE Pipeline

```
YouTube URL
   ↓
yt-dlp (free)
   ↓
Offline Whisper (free, no API key!)
   ↓
Ollama (local, free, no API key!)
   ↓
20 MCQ Questions
```

**Total Cost: $0** 💰

---

## 🔧 Model Recommendations

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `gemma2:2b` | ~2GB | ⚡⚡⚡ Fastest | 👍 Good | Quick MCQs |
| `llama3` | ~4.7GB | ⚡⚡ Fast | 👍👍 Better | Quality MCQs |
| `mistral` | ~4.1GB | ⚡⚡ Fast | 👍👍 Better | Balanced |

**Recommendation:** Start with `gemma2:2b` - it's fast and good enough for MCQs.

---

## 🎯 Using Different Models

In your code, you can specify the model:

```python
generator = YouTubeQuizGenerator(
    llm_provider="ollama",
    llm_model="llama3"  # or "mistral", "gemma2:2b", etc.
)
```

Or set it in the environment:
```powershell
$env:OLLAMA_MODEL="llama3"
```

---

## 🆘 Troubleshooting

**"Cannot connect to Ollama"**
- Make sure Ollama is running: `ollama serve`
- Check if it's accessible: http://localhost:11434
- Restart Ollama if needed

**"Model not found"**
- Pull the model first: `ollama pull gemma2:2b`
- List available models: `ollama list`

**"Request timed out"**
- Try a smaller model (gemma2:2b instead of llama3)
- Or chunk the transcript (coming soon!)

**"Ollama not detected"**
- Make sure Ollama is running
- Check: http://localhost:11434/api/tags
- Should return JSON with available models

---

## ✅ Verification

Test Ollama directly:

```python
import requests

response = requests.get("http://localhost:11434/api/tags")
print(response.json())
```

You should see a list of available models.

---

## 🎉 You're All Set!

Your script now:
- ✅ Auto-detects Ollama if running
- ✅ Falls back to Gemini if Ollama not available
- ✅ Uses local, free LLM
- ✅ No API keys needed
- ✅ Works completely offline

**Total cost: $0** 🚀



