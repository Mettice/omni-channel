#!/usr/bin/env python3
"""
Entry point for running the Omni AI server.

Usage:
    python run.py
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from retell.server import main

if __name__ == "__main__":
    asyncio.run(main())
