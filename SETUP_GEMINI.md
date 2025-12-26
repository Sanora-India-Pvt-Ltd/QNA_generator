# 🚀 Quick Setup: Use Gemini (FREE) Instead of OpenAI

## ✅ Problem Solved

Your code was defaulting to OpenAI, which requires `sk-proj-*` keys that don't work.  
**Now Gemini is the DEFAULT** - completely free, no credit card needed!

---

## 🎯 Step 1: Get Your FREE Gemini API Key

1. Go to: **https://aistudio.google.com/app/apikey**
2. Sign in with Google
3. Click **"Create API Key"**
4. Copy your key (starts with `AIza...`)

---

## 🎯 Step 2: Set Environment Variable (Windows)

**PowerShell:**
```powershell
$env:GEMINI_API_KEY="AIzaSy...your-key-here"
```

**Permanent (survives restart):**
```powershell
setx GEMINI_API_KEY "AIzaSy...your-key-here"
```

**Verify:**
```powershell
echo $env:GEMINI_API_KEY
```

---

## 🎯 Step 3: Install Dependencies

```powershell
pip install google-generativeai
```

Or install everything:
```powershell
pip install -r requirements.txt
```

---

## 🎯 Step 4: Run Your Script!

```powershell
python youtube_quiz_generator.py "https://youtu.be/DFbyL_GwbUU?si=Mv6poQiDKPhvBjCP"
```

**You should now see:**
```
✓ Using Gemini API (FREE tier)
Fetching transcript from: https://youtu.be/...
```

**NO MORE OpenAI errors!** 🎉

---

## ✅ What Changed

- ✅ **Default provider**: Changed from OpenAI → **Gemini**
- ✅ **Auto-detection**: If `GEMINI_API_KEY` is set, uses Gemini automatically
- ✅ **Free tier**: 60 requests/min, 1,500 requests/day
- ✅ **No credit card**: Just sign in with Google

---

## 🎯 Your Complete FREE Pipeline

```
YouTube URL
   ↓
yt-dlp (free)
   ↓
Offline Whisper (free, no API key!)
   ↓
Gemini API (FREE tier!)
   ↓
20 MCQ Questions
```

**Total Cost: $0** 💰

---

## 🔧 If You Still See "Using OpenAI API"

1. **Check environment variable:**
   ```powershell
   echo $env:GEMINI_API_KEY
   ```

2. **If empty, set it:**
   ```powershell
   $env:GEMINI_API_KEY="your-key-here"
   ```

3. **Restart PowerShell** (if using `setx`)

4. **Run again**

---

## ✅ Verification

To test if your key works:

```python
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.0-pro")
response = model.generate_content("Say hello!")
print(response.text)
```

If you see "Hello!" or similar → **Your key works!** ✅

---

## 🎉 You're All Set!

Your script now:
- ✅ Uses **Gemini by default** (free)
- ✅ Falls back to Whisper if transcripts unavailable (free)
- ✅ Generates 20 MCQ questions (free)
- ✅ **Total cost: $0**

No more OpenAI errors! 🚀

