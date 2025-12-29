"""
Service layer that bridges FastAPI to the core quiz generation logic
"""
import sys
import os

# Add parent directory to path to import youtube_quiz_generator
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from youtube_quiz_generator import generate_quiz_from_url


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


