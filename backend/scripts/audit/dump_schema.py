import asyncio
import os
import sys

# Add the app directory to the sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from sqlalchemy import inspect, text
from app.core.db import async_session_maker, engine

async def dump_schema():
    async with engine.connect() as conn:
        tables = [
            'media_assets', 'participant_tracks', 'feature_extractions', 
            'behavioral_metrics', 'nts_scores', 'nts_visual_reports', 
            'processing_jobs', 'meetings'
        ]
        
        for table_name in tables:
            print(f"--- Table: {table_name} ---")
            
            # Columns
            result = await conn.execute(text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}';
            """))
            print("Columns:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")
                
            # Count
            try:
                count_res = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = count_res.scalar()
                print(f"Count: {count}")
            except Exception as e:
                print(f"Count: Error - {e}")
                
            print("\n")

if __name__ == "__main__":
    asyncio.run(dump_schema())
