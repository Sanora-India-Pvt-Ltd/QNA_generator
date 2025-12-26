# 🆓 Gemini Free API Setup Guide

## Why Use Gemini?

✅ **100% FREE** - Generous free tier (60 requests/minute, 1,500 requests/day)  
✅ **No credit card required**  
✅ **High quality** - Google's latest Gemini models  
✅ **Easy setup** - Get API key in 2 minutes  

---

## 🚀 Quick Setup (2 Minutes)

### Step 1: Get Your Free Gemini API Key

1. Go to: **https://makersuite.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy your API key (starts with `AIza...`)

### Step 2: Set Environment Variable

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="AIzaSy...your-key-here"
```

**Windows CMD:**
```cmd
set GEMINI_API_KEY=AIzaSy...your-key-here
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="AIzaSy...your-key-here"
```

### Step 3: Run the Script!

```bash
python youtube_quiz_generator.py "https://youtu.be/VIDEO_ID"
```

The script will automatically detect `GEMINI_API_KEY` and use Gemini! 🎉

---

## 📊 Free Tier Limits

| Limit | Free Tier |
|-------|-----------|
| Requests per minute | 60 |
| Requests per day | 1,500 |
| Cost | **$0** |

**For 20 questions per video:**
- You can process **75 videos per day** (1,500 ÷ 20)
- That's plenty for most use cases!

---

## 🔧 Manual Setup (If Not Using Environment Variable)

If you prefer to enter the key when prompted:

```bash
python youtube_quiz_generator.py
```

When asked to choose:
- Enter `2` for Gemini
- Paste your API key when prompted

---

## 💻 Python Code Example

```python
from youtube_quiz_generator import YouTubeQuizGenerator

# Using Gemini (free!)
generator = YouTubeQuizGenerator(
    llm_provider="gemini",
    api_key="AIzaSy...your-key-here"
)

results = generator.process("https://youtu.be/VIDEO_ID", num_questions=20)
generator.print_questions(results)
```

---

## 🆚 Gemini vs OpenAI

| Feature | Gemini (Free) | OpenAI |
|---------|---------------|--------|
| Cost | **FREE** | Paid |
| Setup | 2 minutes | Requires credit card |
| Quality | Excellent | Excellent |
| Rate Limits | 60/min, 1500/day | Varies by plan |
| Best For | Personal use, testing | Production, high volume |

---

## 🎯 Recommended Models

- **`gemini-1.0-pro`** (default) - Stable, accurate, perfect for questions, works on free tier
- **`gemini-1.5-flash-latest`** - Faster, if available on your account

You can specify the model:
```python
generator = YouTubeQuizGenerator(
    llm_provider="gemini",
    api_key="your-key",
    llm_model="gemini-1.0-pro"  # Optional (default)
)
```

---

## ✅ Verification

To test if your API key works:

```python
import google.generativeai as genai

genai.configure(api_key="your-key-here")
model = genai.GenerativeModel("gemini-1.0-pro")
response = model.generate_content("Say hello!")
print(response.text)
```

If you see "Hello!" or similar, your key works! ✅

---

## 🆘 Troubleshooting

**"google-generativeai not found"**
```bash
pip install google-generativeai
```

**"Invalid API key"**
- Make sure you copied the full key
- Check for extra spaces
- Verify key at https://makersuite.google.com/app/apikey

**"Rate limit exceeded"**
- Free tier: 60 requests/minute
- Wait a minute and try again
- Or upgrade to paid tier for higher limits

---

## 🎉 You're All Set!

Now you can generate unlimited MCQ questions using:
- ✅ **Offline Whisper** (free transcription)
- ✅ **Gemini API** (free question generation)

**Total cost: $0** 🎊

