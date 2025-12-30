#!/bin/bash
# Quick start script for Linux/Mac

echo "Setting up environment..."
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set!"
    echo "Please set it with: export DATABASE_URL='postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/mcq_db'"
    exit 1
fi

echo "Starting FastAPI server..."
uvicorn api_pg_mcq:app --reload --host 0.0.0.0 --port 8000

