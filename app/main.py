"""
FastAPI REST API for YouTube MCQ Generator

Endpoints:
    POST /generate-quiz - Generate 20 MCQs from YouTube URL
    POST /generate-quiz-from-video - Generate 20 MCQs from direct video URL (S3, CDN, HTTPS)
    POST /generate-course-quiz - Generate MCQs from multiple course videos
    GET /health - Health check endpoint
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    QuizRequest, QuizResponse,
    VideoURLRequest, CourseVideoRequest, CourseQuizResponse
)
from app.services.quiz_service import (
    generate_quiz, create_quiz, create_quiz_from_video_url, create_course_quiz
)

app = FastAPI(
    title="Video MCQ Generator API",
    description="Generate 20 unique multiple-choice questions from YouTube videos or direct video URLs (S3, CDN, HTTPS)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Video MCQ Generator API"}


@app.post("/generate-quiz", response_model=QuizResponse)
def generate_quiz_api(payload: QuizRequest):
    """
    Generate 20 unique MCQs from a video URL (YouTube or direct video URL)
    
    Automatically detects URL type and routes to appropriate handler:
    - YouTube URLs → YouTube Transcript API (with Whisper fallback)
    - Direct video URLs (S3, CDN, HTTPS) → Video download + Whisper transcription
    
    Pipeline:
    1. Detect URL type and fetch transcript
    2. Agent-03: Web knowledge enrichment
    3. Generate 20 unique MCQs using Ollama
    
    Args:
        payload: QuizRequest containing url (YouTube or direct video URL)
        
    Returns:
        QuizResponse with exactly 20 MCQ questions
        
    Raises:
        HTTPException: If quiz generation fails
    """
    try:
        result = generate_quiz(str(payload.url))
        return result
    except ValueError as e:
        # Handle unsupported URL type
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Handle expected errors (e.g., wrong question count)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Quiz generation failed: {str(e)}"
        )


@app.post("/generate-quiz-from-video", response_model=QuizResponse)
def generate_quiz_from_video(payload: VideoURLRequest):
    """
    Generate 20 unique MCQs from a direct video URL (S3, CDN, HTTPS)
    
    This endpoint works with any HTTP/HTTPS video URL - no YouTube, no yt-dlp, no cookies.
    Perfect for course videos stored on S3, CDN, or any web server.
    
    Pipeline:
    1. Download video from URL
    2. Extract audio using FFmpeg
    3. Transcribe with Whisper
    4. Agent-03: Web knowledge enrichment
    5. Generate 20 unique MCQs using Ollama
    
    Args:
        payload: VideoURLRequest containing video_url
        
    Returns:
        QuizResponse with exactly 20 MCQ questions
        
    Raises:
        HTTPException: If quiz generation fails
    """
    try:
        result = create_quiz_from_video_url(str(payload.video_url))
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quiz generation failed: {str(e)}"
        )


@app.post("/generate-course-quiz", response_model=CourseQuizResponse)
def generate_course_quiz(payload: CourseVideoRequest):
    """
    Generate MCQs from multiple course video URLs
    
    This endpoint processes multiple videos and returns quiz results for each.
    Perfect for course-level quiz generation where you have multiple video lessons.
    
    Args:
        payload: CourseVideoRequest containing course_id (optional) and video_urls list
        
    Returns:
        CourseQuizResponse with quiz results for each video
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        result = create_course_quiz(
            payload.course_id or "",
            list(payload.video_urls)
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Course quiz generation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



