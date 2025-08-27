"""Test configuration"""

import os
import sys
import pytest

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure test environment
os.environ["DATABASE_URL"] = "postgresql://app_user:app_password@localhost:5433/orders"
os.environ["TEMPORAL_HOST"] = "localhost:7233"
