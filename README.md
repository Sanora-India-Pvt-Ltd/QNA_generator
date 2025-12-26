# YouTube URL to MCQ Questions Generator

A Python application that automatically generates 20 multiple-choice questions (MCQ) from YouTube video transcripts using AI.

## Pipeline

```
YouTube URL
   ↓
YouTube Transcript API (or Whisper fallback)
   ↓
Transcript Cleaning
   ↓
LLM Prompting (AI/ML-specific)
   ↓
20 MCQ Questions
```

## Features

- ✅ Fetches transcripts from YouTube videos automatically
- ✅ **Offline Whisper fallback**: Automatically uses offline Whisper (no API key needed!) when YouTube transcripts are unavailable
- ✅ Downloads and transcribes audio for videos without captions
- ✅ Cleans and processes transcript text
- ✅ Detects specialization/topic (AI/ML, Technology, General)
- ✅ Generates 20 high-quality MCQ questions using **OpenAI GPT** or **Google Gemini** (free tier available!)
- ✅ Questions cover text content, specialization, and video context
- ✅ Includes correct answers and explanations
- ✅ Exports results to JSON format

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. **Install FFmpeg** (required for Whisper fallback):
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use:
     ```bash
     # Using chocolatey
     choco install ffmpeg
     
     # Using winget
     winget install ffmpeg
     ```
   - **Linux**: 
     ```bash
     sudo apt-get install ffmpeg  # Debian/Ubuntu
     sudo yum install ffmpeg      # CentOS/RHEL
     ```
   - **Mac**: 
     ```bash
     brew install ffmpeg
     ```
   
   Note: FFmpeg is only needed if YouTube transcripts are unavailable (for Whisper fallback)

4. **Set up API key for question generation** (NOT needed for Whisper - it's offline):
   
   **Option A: Use Gemini (FREE - Recommended!)**
   - Get free API key: https://makersuite.google.com/app/apikey
   - Set environment variable:
     ```bash
     # Windows PowerShell
     $env:GEMINI_API_KEY="your-gemini-api-key-here"
     
     # Windows CMD
     set GEMINI_API_KEY=your-gemini-api-key-here
     
     # Linux/Mac
     export GEMINI_API_KEY="your-gemini-api-key-here"
     ```
   
   **Option B: Use OpenAI**
   - Get API key: https://platform.openai.com/
   - Set environment variable:
     ```bash
     # Windows PowerShell
     $env:OPENAI_API_KEY="your-api-key-here"
     
     # Windows CMD
     set OPENAI_API_KEY=your-api-key-here
     
     # Linux/Mac
     export OPENAI_API_KEY="your-api-key-here"
     ```
   
   - Option 3: Enter it when prompted by the script

## Usage

### Command Line

```bash
python youtube_quiz_generator.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Or run without arguments to be prompted for the URL:
```bash
python youtube_quiz_generator.py
```

### Python Script

**Using Gemini (Free):**
```python
from youtube_quiz_generator import YouTubeQuizGenerator

# Initialize generator with Gemini
generator = YouTubeQuizGenerator(
    llm_provider="gemini",
    api_key="your-gemini-api-key"
)

# Process YouTube URL
results = generator.process("https://www.youtube.com/watch?v=VIDEO_ID", num_questions=20)

# Print questions
generator.print_questions(results)

# Save to file
generator.save_results(results, "my_quiz.json")
```

**Using OpenAI:**
```python
from youtube_quiz_generator import YouTubeQuizGenerator

# Initialize generator with OpenAI
generator = YouTubeQuizGenerator(
    llm_provider="openai",
    api_key="your-openai-api-key"
)

# Process YouTube URL
results = generator.process("https://www.youtube.com/watch?v=VIDEO_ID", num_questions=20)
```

## Output

The script generates:
- **Transcript Analysis**: Word count, character count, sentence count, and detected specialization
- **20 MCQ Questions**: Each with:
  - Question text
  - 4 options (A, B, C, D)
  - Correct answer
  - Explanation

Results are:
1. Printed to console in readable format
2. Saved to `quiz_results.json` file

## Example Output

```
Question 1: What is the main topic discussed in this video?
  A) Machine Learning Basics
  B) Deep Learning Applications
  C) Neural Network Architecture
  D) Data Preprocessing Techniques
  Correct Answer: A
  Explanation: The video primarily focuses on introducing fundamental concepts of machine learning...
```

## Requirements

- Python 3.7+
- OpenAI API key (get one at https://platform.openai.com/)
- Internet connection (for fetching YouTube transcripts)

## Dependencies

- `youtube-transcript-api`: Fetches transcripts from YouTube videos
- `openai`: OpenAI Python SDK (optional - only if using OpenAI for questions)
- `google-generativeai`: Google Gemini SDK (optional - only if using Gemini for questions)
- `openai-whisper`: Offline Whisper transcription (no API key needed!)
- `torch`, `torchvision`, `torchaudio`: PyTorch for Whisper model
- `yt-dlp`: Downloads audio from YouTube videos (for Whisper fallback)
- `requests`: HTTP library for API calls
- `ffmpeg`: Required system dependency for audio processing (install separately)

## Notes

- **Primary method**: The script first tries YouTube Transcript API (requires captions/subtitles)
- **Fallback method**: If transcripts are unavailable, it automatically downloads audio and uses **offline Whisper** (no API key needed!)
- **Whisper is FREE and OFFLINE**: Uses local Whisper models - no API costs, no rate limits, works offline
- **Whisper model sizes**: Default is "base" (good balance). Options: "tiny", "base", "small", "medium", "large"
- **Question Generation**: Supports both OpenAI and Gemini APIs
  - **Gemini**: Free tier available! Get key at https://makersuite.google.com/app/apikey
  - **OpenAI**: Requires paid API key
- Transcripts are automatically cleaned to remove artifacts like [Music], [Applause], etc.
- Default models: `gpt-4o-mini` (OpenAI) or `gemini-1.0-pro` (Gemini - stable, free tier)
- Questions are generated based on the actual transcript content, ensuring relevance
- Whisper fallback requires FFmpeg to be installed on your system

## Troubleshooting

**Error: "Transcripts are disabled for this video"**
- The script will automatically try Whisper fallback if enabled
- If Whisper also fails, ensure:
  - FFmpeg is installed and in your PATH
  - yt-dlp is installed: `pip install yt-dlp`
  - You have a valid OpenAI API key
  - The video has audio (not just visuals)

**Error: "yt-dlp is required for Whisper fallback"**
- Install yt-dlp: `pip install yt-dlp`
- This is needed when YouTube transcripts are unavailable

**Error: "openai-whisper is required"**
- Install Whisper: `pip install openai-whisper`
- Also install PyTorch: `pip install torch torchvision torchaudio`
- **Note**: Whisper is OFFLINE - no API key needed!

**Error: "FFmpeg not found"**
- Install FFmpeg on your system (see Installation section)
- Ensure FFmpeg is in your system PATH
- Test with: `ffmpeg -version`

**Error: "OpenAI API key is required"**
- Make sure you've set the OPENAI_API_KEY environment variable or entered it when prompted
- **Note**: This is ONLY for question generation (LLM). Whisper works offline without any API key!

**Error: "Invalid YouTube URL"**
- Ensure the URL is a valid YouTube video URL
- Supported formats:
  - `https://www.youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID` (with or without query parameters)
  - `https://www.youtube.com/embed/VIDEO_ID`

**Whisper transcription is slow**
- This is normal - Whisper processes the entire audio file
- Large videos will take longer to transcribe
- Progress messages will indicate when transcription is complete

## License

This project is open source and available for educational purposes.


