@echo off
REM Quick start script for Windows

echo Setting up environment...
if "%DATABASE_URL%"=="" (
    echo WARNING: DATABASE_URL not set!
    echo Please set it with: setx DATABASE_URL "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/mcq_db"
    pause
)

echo Starting FastAPI server...
uvicorn api_pg_mcq:app --reload --host 0.0.0.0 --port 8000

