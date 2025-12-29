"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, AnyUrl
from typing import Dict, List, Optional


class QuizRequest(BaseModel):
    """Request model for quiz generation from YouTube URL"""
    youtube_url: AnyUrl


class VideoURLRequest(BaseModel):
    """Request model for quiz generation from direct video URL (S3, CDN, HTTPS)"""
    video_url: AnyUrl


class CourseVideoRequest(BaseModel):
    """Request model for generating MCQs from multiple course videos"""
    course_id: Optional[str] = None
    video_urls: List[AnyUrl]


class MCQ(BaseModel):
    """Single MCQ question model"""
    question: str
    options: Dict[str, str]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    """Response model containing list of MCQs"""
    questions: List[MCQ]


class VideoQuizResult(BaseModel):
    """Result for a single video quiz generation"""
    video_url: str
    questions: List[MCQ]


class CourseQuizResponse(BaseModel):
    """Response model for course-level quiz generation"""
    course_id: Optional[str] = None
    results: List[VideoQuizResult]



