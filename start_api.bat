@echo off
echo Starting YouTube MCQ Generator API...
echo.
echo API will be available at: http://127.0.0.1:8000
echo Swagger UI: http://127.0.0.1:8000/docs
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause



