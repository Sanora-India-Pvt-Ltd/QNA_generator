"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, AnyUrl
from typing import Dict, List


class QuizRequest(BaseModel):
    """Request model for quiz generation"""
    youtube_url: AnyUrl


class MCQ(BaseModel):
    """Single MCQ question model"""
    question: str
    options: Dict[str, str]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    """Response model containing list of MCQs"""
    questions: List[MCQ]


