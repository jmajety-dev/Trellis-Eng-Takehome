#!/usr/bin/env python3
"""Database migration script"""

import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import create_tables, check_database_connection
from app.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def main():
    """Run database migrations"""
    logger.info("Starting database migration")
    
    try:
        # Check connection first
        if not await check_database_connection():
            logger.error("Database connection failed")
            return 1
        
        # Create tables
        await create_tables()
        logger.info("Database migration completed successfully")
        return 0
        
    except Exception as e:
        logger.error("Database migration failed", error=str(e))
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
