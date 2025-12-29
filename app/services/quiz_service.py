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


def create_quiz(youtube_url: str):
    """
    Generate quiz from YouTube URL
    
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



