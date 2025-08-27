#!/usr/bin/env python3
"""Quick test script to verify the system is working"""

import asyncio
import sys
import os
import time

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import check_database_connection, create_tables
from app.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def test_database():
    """Test database connectivity"""
    print("Testing database connection...")
    
    try:
        if await check_database_connection():
            print("Database connection successful")
            
            # Try to create tables
            await create_tables()
            print("Database tables created/verified")
            return True
        else:
            print("Database connection failed")
            return False
    except Exception as e:
        print(f"Database test failed: {e}")
        return False


async def test_temporal():
    """Test Temporal connectivity"""
    print("Testing Temporal connection...")
    
    try:
        from temporalio.client import Client
        from app.utils.config import settings
        
        client = await Client.connect(settings.temporal_host)
        print("Temporal connection successful")
        return True
    except Exception as e:
        print(f"Temporal connection failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🧪 Running system health checks...\n")
    
    # Test database
    db_ok = await test_database()
    
    # Test Temporal
    temporal_ok = await test_temporal()
    
    print("\n📊 Test Results:")
    print(f"Database: {'OK' if db_ok else 'FAILED'}")
    print(f"Temporal: {'OK' if temporal_ok else 'FAILED'}")

    if db_ok and temporal_ok:
        print("\nAll systems are ready!")
        return 0
    else:
        print("\n Some systems are not ready. Check the setup and try again.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
