# Quick Start Guide - Offline Whisper Setup

## ✅ Complete Installation (Windows)

### Step 1: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

This installs:
- `youtube-transcript-api` - For YouTube captions
- `openai` - For LLM question generation (needs API key)
- `openai-whisper` - **OFFLINE Whisper (no API key!)**
- `yt-dlp` - For downloading YouTube audio
- `torch` - PyTorch for Whisper models

### Step 2: Install FFmpeg

**Option A: Using winget (Recommended)**
```powershell
winget install ffmpeg
```

**Option B: Using Chocolatey**
```powershell
choco install ffmpeg
```

**Option C: Manual Download**
1. Download from: https://ffmpeg.org/download.html
2. Extract and add `ffmpeg/bin` to your system PATH
3. Verify: `ffmpeg -version`

### Step 3: Set OpenAI API Key (Only for Question Generation)

```powershell
$env:OPENAI_API_KEY="sk-proj-your-key-here"
```

**Note**: This is ONLY for generating questions. Whisper works completely offline!

### Step 4: Run the Script

```powershell
python youtube_quiz_generator.py "https://youtu.be/VIDEO_ID"
```

## 🎯 What Happens

1. **First**: Tries YouTube Transcript API (fast, free)
2. **If unavailable**: Automatically downloads audio and uses **offline Whisper**
3. **Then**: Generates 20 MCQ questions using LLM

## 🚀 Whisper Model Sizes

You can choose the model size when initializing:

```python
generator = YouTubeQuizGenerator(
    openai_api_key="your-key",
    whisper_model="base"  # Options: "tiny", "base", "small", "medium", "large"
)
```

| Model  | Speed      | Accuracy | Size   |
|--------|------------|----------|--------|
| tiny   | ⚡⚡⚡ Fastest | 👍 Good  | ~75MB  |
| base   | ⚡⚡ Fast    | 👍👍 Better | ~150MB |
| small  | ⚡ Balanced | 👍👍👍 Great | ~500MB |
| medium | 🐢 Slower  | 🔥 Best  | ~1.5GB |
| large  | 🐢🐢 Slowest | 🔥🔥 Excellent | ~3GB |

**Recommendation**: Start with `"base"` - good balance of speed and accuracy.

## ✅ Advantages of Offline Whisper

- ✅ **No API key needed** for transcription
- ✅ **No API costs** - completely free
- ✅ **No rate limits** - process as many videos as you want
- ✅ **Works offline** - no internet needed after model download
- ✅ **Privacy** - audio never leaves your machine
- ✅ **Fast** - local processing is often faster than API calls

## 🔧 Troubleshooting

**"openai-whisper not found"**
```powershell
pip install openai-whisper torch torchvision torchaudio
```

**"FFmpeg not found"**
- Make sure FFmpeg is installed and in PATH
- Test: `ffmpeg -version`

**Model download is slow**
- First run downloads the model (~150MB for "base")
- Subsequent runs use cached model (instant)

**Transcription is slow**
- Normal for long videos
- "base" model: ~1-2x video length
- "small" model: ~2-3x video length
- Consider using "tiny" for faster processing

## 🎉 You're All Set!

The script now uses **offline Whisper** - no more API key issues for transcription!



