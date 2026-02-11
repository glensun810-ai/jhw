#!/usr/bin/env python3
"""
Test script to verify logging functionality
"""
import os
import sys
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_logging():
    print("Testing logging functionality...")
    
    # Import and setup logging
    from wechat_backend.logging_config import setup_logging, app_logger, api_logger, db_logger, wechat_logger
    
    # Setup logging with DEBUG level for testing
    setup_logging(log_level='DEBUG')
    
    # Test different loggers
    app_logger.debug("This is a debug message from app logger")
    app_logger.info("This is an info message from app logger")
    app_logger.warning("This is a warning message from app logger")
    app_logger.error("This is an error message from app logger")
    
    api_logger.debug("This is a debug message from API logger")
    api_logger.info("This is an info message from API logger")
    api_logger.warning("This is a warning message from API logger")
    api_logger.error("This is an error message from API logger")
    
    db_logger.debug("This is a debug message from DB logger")
    db_logger.info("This is an info message from DB logger")
    db_logger.warning("This is a warning message from DB logger")
    db_logger.error("This is an error message from DB logger")
    
    wechat_logger.debug("This is a debug message from WeChat logger")
    wechat_logger.info("This is an info message from WeChat logger")
    wechat_logger.warning("This is a warning message from WeChat logger")
    wechat_logger.error("This is an error message from WeChat logger")
    
    print("\nCheck the logs/app.log file to verify logging is working.")
    
    # Also test that the logs directory was created
    logs_dir = project_root / 'logs'
    if logs_dir.exists():
        print(f"\n✓ Logs directory created at: {logs_dir}")
        log_file = logs_dir / 'app.log'
        if log_file.exists():
            print(f"✓ Log file exists: {log_file}")
            # Show last few lines of log
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"\nLast 5 lines of log file:")
                for line in lines[-5:]:
                    print(line.strip())
        else:
            print(f"⚠ Log file does not exist yet: {log_file}")
    else:
        print(f"⚠ Logs directory was not created: {logs_dir}")

if __name__ == "__main__":
    test_logging()