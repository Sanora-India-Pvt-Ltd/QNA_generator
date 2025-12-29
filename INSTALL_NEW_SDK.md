# 🚀 Install New Gemini SDK (google-genai)

## ✅ Quick Setup

### Step 1: Uninstall Old SDK

```powershell
pip uninstall google-generativeai -y
```

### Step 2: Install New SDK

```powershell
pip install --upgrade google-genai
```

### Step 3: Verify

```powershell
python -c "from google import genai; print('✓ New SDK ready!')"
```

---

## 📦 Or Update All Dependencies

```powershell
pip install -r requirements.txt
```

This will automatically install `google-genai` (new) instead of `google-generativeai` (old).

---

## ✅ What Changed

- ❌ **Old**: `google-generativeai` (deprecated)
- ✅ **New**: `google-genai` (official, current)

---

## 🎯 After Installation

Run your script:

```powershell
python youtube_quiz_generator.py "https://youtu.be/VIDEO_ID"
```

You should see:
- ✅ No deprecated warnings
- ✅ No 404 errors
- ✅ Successful question generation

---

## 🆘 Troubleshooting

**"No module named 'google.genai'"**
- Make sure you installed: `pip install google-genai`
- Not: `pip install google-generativeai` (old)

**"Client is not defined"**
- Make sure you're using: `from google import genai`
- Then: `genai.Client(api_key=...)`

---

## ✅ You're Ready!

The code is updated to use the new SDK. Just install it and run! 🚀



