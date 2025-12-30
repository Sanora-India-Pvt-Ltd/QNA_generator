"""
Verify Data in MySQL Database
Run this script to check if your MCQs are saved in MySQL
"""

import asyncio
import os
import sys
from typing import Any
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Integer, BigInteger, TIMESTAMP
from sqlalchemy.dialects.mysql import JSON

class Base(DeclarativeBase):
    pass

class VideoMCQ(Base):
    __tablename__ = "video_mcqs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    url: Mapped[str] = mapped_column(Text)
    mcq_count: Mapped[int] = mapped_column(Integer, default=20)
    questions: Mapped[dict] = mapped_column(JSON)
    generator: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(TIMESTAMP, nullable=False)
    updated_at: Mapped[Any] = mapped_column(TIMESTAMP, nullable=False)

async def verify_database():
    database_url = os.getenv("DATABASE_URL", "")
    
    if not database_url:
        print("❌ DATABASE_URL not set!")
        print("\nPlease set it with:")
        print('  Windows PowerShell: $env:DATABASE_URL = "mysql+aiomysql://root:password@127.0.0.1:3306/mcq_db"')
        return
    
    print("=" * 60)
    print("MySQL Database Verification")
    print("=" * 60)
    print(f"🔗 Connecting to: {database_url.split('@')[1] if '@' in database_url else 'database'}\n")
    
    try:
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        
        async with engine.begin() as conn:
            # Check if table exists
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'video_mcqs'
            """))
            table_exists = result.scalar() > 0
            
            if not table_exists:
                print("❌ Table 'video_mcqs' does not exist!")
                print("   Run setup_database_mysql.sql to create it.")
                return
            
            print("✅ Table 'video_mcqs' exists\n")
            
            # Count total records
            result = await conn.execute(text("SELECT COUNT(*) FROM video_mcqs"))
            total_count = result.scalar()
            print(f"📊 Total videos saved: {total_count}\n")
            
            if total_count == 0:
                print("⚠️  No videos found in database yet.")
                print("   Generate some MCQs using POST /generate-and-save")
                return
            
            # Get all videos
            result = await conn.execute(text("""
                SELECT 
                    video_id,
                    url,
                    mcq_count,
                    created_at,
                    updated_at
                FROM video_mcqs 
                ORDER BY created_at DESC 
                LIMIT 10
            """))
            
            videos = result.fetchall()
            
            print("=" * 60)
            print("Recent Videos (Last 10)")
            print("=" * 60)
            
            for idx, video in enumerate(videos, 1):
                video_id, url, mcq_count, created_at, updated_at = video
                print(f"\n{idx}. Video ID: {video_id}")
                print(f"   URL: {url[:60]}..." if len(url) > 60 else f"   URL: {url}")
                print(f"   MCQs: {mcq_count}")
                print(f"   Created: {created_at}")
                print(f"   Updated: {updated_at}")
            
            # Check JSON data
            print("\n" + "=" * 60)
            print("Verifying JSON Data")
            print("=" * 60)
            
            result = await conn.execute(text("""
                SELECT 
                    video_id,
                    JSON_LENGTH(questions, '$.questions') as question_count,
                    JSON_EXTRACT(questions, '$.questions[0].question') as first_question
                FROM video_mcqs 
                LIMIT 3
            """))
            
            json_data = result.fetchall()
            for video_id, q_count, first_q in json_data:
                print(f"\nVideo ID: {video_id}")
                print(f"  Questions in JSON: {q_count}")
                if first_q:
                    first_q_clean = first_q.strip('"')[:80] if first_q else "N/A"
                    print(f"  First question: {first_q_clean}...")
            
            print("\n" + "=" * 60)
            print("✅ Database verification complete!")
            print("=" * 60)
        
        await engine.dispose()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_database())

