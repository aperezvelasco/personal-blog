"""
Weekly local daemon scheduler for compiling manual posts and papers.

This script executes compile_all_posts every 7 days in an infinite loop
to keep the local papers database fresh.
"""

import os
import sys
import time
from datetime import datetime
from typing import NoReturn

# Ensure current directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from compile_blog import compile_all_posts


def run_scheduler() -> NoReturn:
    """
    Run an infinite loop that triggers compile_all_posts every 7 days.

    Maintains logs in the console with timestamps, catches and displays
    exceptions, and handles sleeping between execution cycles.
    """
    # Run interval of 7 days in seconds
    interval_seconds: int = 7 * 24 * 60 * 60

    print(f"[{datetime.now().isoformat()}] Starting weekly paper scheduler...")

    while True:
        try:
            now: str = datetime.now().isoformat()
            print(f"[{now}] Triggering scheduled blog compilation...")
            compile_all_posts()
            print(f"[{now}] Compilation complete. Next run in 7 days.")
        except Exception as e:
            now_err: str = datetime.now().isoformat()
            print(f"[{now_err}] Error during scheduled execution: {e}")

        # Sleep for 7 days
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_scheduler()
