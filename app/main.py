"""
FastAPI REST API for YouTube MCQ Generator

Endpoints:
    POST /generate-quiz - Generate 20 MCQs from YouTube URL
    GET /health - Health check endpoint
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import QuizRequest, QuizResponse
from app.services.quiz_service import create_quiz

app = FastAPI(
    title="YouTube MCQ Generator API",
    description="Generate 20 unique multiple-choice questions from YouTube video transcripts",
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
    return {"status": "healthy", "service": "YouTube MCQ Generator API"}


@app.post("/generate-quiz", response_model=QuizResponse)
def generate_quiz(payload: QuizRequest):
    """
    Generate 20 unique MCQs from a YouTube video URL
    
    Pipeline:
    1. Fetch transcript (YouTube API or Whisper fallback)
    2. Agent-03: Web knowledge enrichment
    3. Generate 20 unique MCQs using Ollama
    
    Args:
        payload: QuizRequest containing youtube_url
        
    Returns:
        QuizResponse with exactly 20 MCQ questions
        
    Raises:
        HTTPException: If quiz generation fails
    """
    try:
        result = create_quiz(str(payload.youtube_url))
        return result
    except RuntimeError as e:
        # Handle expected errors (e.g., wrong question count)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Quiz generation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


