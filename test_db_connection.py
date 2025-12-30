"""
Test MySQL Database Connection
Run this to verify your DATABASE_URL is configured correctly
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection():
    database_url = os.getenv("DATABASE_URL", "")
    
    if not database_url:
        print("❌ DATABASE_URL not set!")
        print("\nPlease set it with:")
        print('  Windows PowerShell: $env:DATABASE_URL = "mysql+aiomysql://root:password@127.0.0.1:3306/mcq_db"')
        print('  Windows CMD: setx DATABASE_URL "mysql+aiomysql://root:password@127.0.0.1:3306/mcq_db"')
        print('  Linux/Mac: export DATABASE_URL="mysql+aiomysql://root:password@127.0.0.1:3306/mcq_db"')
        return
    
    print(f"🔗 Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'database'}")
    
    try:
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        
        async with engine.begin() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database connection successful!")
            
            # Check if database exists
            result = await conn.execute(text("SELECT DATABASE()"))
            db_name = result.scalar()
            print(f"📊 Connected to database: {db_name}")
            
            # Check if table exists
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'video_mcqs'
            """))
            table_exists = result.scalar() > 0
            
            if table_exists:
                print("✅ Table 'video_mcqs' exists!")
                
                # Count records
                result = await conn.execute(text("SELECT COUNT(*) FROM video_mcqs"))
                count = result.scalar()
                print(f"📝 Records in table: {count}")
            else:
                print("⚠️  Table 'video_mcqs' does not exist!")
                print("   Run setup_database_mysql.sql to create it.")
        
        print("\n✅ All checks passed! You're ready to use the API.")
        
    except Exception as e:
        print(f"\n❌ Connection failed!")
        print(f"   Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if MySQL server is running")
        print("2. Verify username and password in DATABASE_URL")
        print("3. Ensure database 'mcq_db' exists")
        print("4. Check if port 3306 is correct")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("=" * 50)
    print("MySQL Database Connection Test")
    print("=" * 50)
    asyncio.run(test_connection())

