-- PostgreSQL Database Setup for Video MCQ Generator
-- Run this once in psql / pgAdmin

CREATE TABLE IF NOT EXISTS video_mcqs (
  id BIGSERIAL PRIMARY KEY,
  video_id VARCHAR(32) UNIQUE NOT NULL,
  url TEXT NOT NULL,
  mcq_count INT NOT NULL DEFAULT 20,
  questions JSONB NOT NULL,
  generator JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_mcqs_url ON video_mcqs(url);
CREATE INDEX IF NOT EXISTS idx_video_mcqs_video_id ON video_mcqs(video_id);

