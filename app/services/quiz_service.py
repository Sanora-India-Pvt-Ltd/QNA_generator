"""
Service layer that bridges FastAPI to the core quiz generation logic
"""
import sys
import os

# Add parent directory to path to import youtube_quiz_generator
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from youtube_quiz_generator import generate_quiz_from_url, generate_quiz_from_video_url


def generate_quiz(url: str):
    """
    Generate quiz from URL - automatically routes based on URL type
    
    Supports:
    - YouTube URLs (youtube.com, youtu.be)
    - Direct video URLs (S3, CDN, HTTPS with .mp4, .mov, .mkv, .webm extensions)
    
    Args:
        url: Video URL (YouTube or direct video URL)
        
    Returns:
        dict: {"questions": [...]} with 20 MCQ dictionaries
        
    Raises:
        ValueError: If URL type is unsupported
        Exception: If quiz generation fails
    """
    url = url.strip()
    
    # 1️⃣ YouTube URLs
    if "youtube.com" in url or "youtu.be" in url:
        questions = generate_quiz_from_url(url)
        return {"questions": questions}
    
    # 2️⃣ Direct video URLs (S3 / CDN / MP4)
    if url.startswith("http") and (
        url.endswith((".mp4", ".mov", ".mkv", ".webm")) or
        ".mp4" in url or ".mov" in url or ".mkv" in url or ".webm" in url
    ):
        questions = generate_quiz_from_video_url(url)
        return {"questions": questions}
    
    # 3️⃣ Generic HTTPS URLs (assume video if not YouTube)
    if url.startswith("http"):
        # Try as direct video URL (will fail gracefully if not a video)
        try:
            questions = generate_quiz_from_video_url(url)
            return {"questions": questions}
        except Exception:
            raise ValueError(
                f"Unsupported URL type: {url}\n"
                "Supported formats:\n"
                "  - YouTube URLs (youtube.com, youtu.be)\n"
                "  - Direct video URLs (S3, CDN with .mp4, .mov, .mkv, .webm extensions)"
            )
    
    raise ValueError(
        f"Invalid URL format: {url}\n"
        "URL must be a valid HTTP/HTTPS URL"
    )


def create_quiz(youtube_url: str):
    """
    Generate quiz from YouTube URL (legacy function - kept for backward compatibility)
    
    Args:
        youtube_url: YouTube video URL (string)
        
    Returns:
        dict: {"questions": [...]} with 20 MCQ dictionaries
        
    Raises:
        Exception: If quiz generation fails
    """
    questions = generate_quiz_from_url(youtube_url)
    return {"questions": questions}


def create_quiz_from_video_url(video_url: str):
    """
    Generate quiz from direct video URL (S3, CDN, HTTPS)
    
    Args:
        video_url: HTTP/HTTPS URL to video file (string)
        
    Returns:
        dict: {"questions": [...]} with 20 MCQ dictionaries
        
    Raises:
        Exception: If quiz generation fails
    """
    questions = generate_quiz_from_video_url(video_url)
    return {"questions": questions}


def create_course_quiz(course_id: str, video_urls: list):
    """
    Generate quizzes from multiple course video URLs
    
    Args:
        course_id: Optional course identifier
        video_urls: List of video URLs (strings)
        
    Returns:
        dict: {"course_id": ..., "results": [...]} with quiz results per video
        
    Raises:
        Exception: If quiz generation fails for any video
    """
    results = []
    
    for video_url in video_urls:
        try:
            questions = generate_quiz_from_video_url(str(video_url))
            results.append({
                "video_url": str(video_url),
                "questions": questions
            })
        except Exception as e:
            # Continue with other videos even if one fails
            results.append({
                "video_url": str(video_url),
                "questions": [],
                "error": str(e)
            })
    
    return {
        "course_id": course_id,
        "results": results
    }



