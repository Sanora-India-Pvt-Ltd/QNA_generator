# ⚡ Performance Tips for Faster Processing

## 🐌 Why It's Slow

1. **Whisper Transcription** - CPU-based transcription is slow (1-3x video length)
2. **Ollama Processing** - Generating 20 questions takes 1-3 minutes
3. **Large Transcripts** - Longer videos = longer processing

## ⚡ Speed Improvements

### 1. Use Faster Whisper Model

In `youtube_quiz_generator.py`, change:
```python
WhisperAudioTranscriber(model="base")  # Current
```

To:
```python
WhisperAudioTranscriber(model="tiny")  # 3x faster, slightly less accurate
```

### 2. Use Faster Ollama Model

Change model in code:
```python
OLLAMA_MODEL = "gemma2:2b"  # Fast (current)
```

Even faster options:
```python
OLLAMA_MODEL = "gemma2:1b"  # Very fast, smaller
OLLAMA_MODEL = "phi3:mini"  # Fast alternative
```

### 3. Reduce Transcript Length

Already optimized - code limits to 4000 characters.

### 4. Use YouTube Transcripts When Available

The code tries YouTube transcripts first (fast) before Whisper (slow).

## 📊 Expected Times

| Step | Time |
|------|------|
| YouTube Transcript | 2-5 seconds |
| Whisper (tiny) | 1-2x video length |
| Whisper (base) | 2-3x video length |
| Ollama (gemma2:2b) | 1-3 minutes |
| Ollama (llama3) | 3-5 minutes |

## 🎯 Quick Wins

1. **Use YouTube transcripts** - Much faster than Whisper
2. **Use tiny Whisper model** - 3x faster transcription
3. **Use gemma2:2b** - Fastest good-quality model
4. **Shorter videos** - Process shorter videos for testing

## 💡 For Production

- Use GPU for Whisper (10x faster)
- Use larger Ollama models for better quality (slower)
- Cache transcripts to avoid re-processing

