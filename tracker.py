"""
Task tracking functionality for the Task Time Tracker application.

This module provides functions to log tasks to persistent storage,
including duration and timestamp information. It handles file operations
and maintains the correct format for task logs.
"""

import os
import json
import datetime
from typing import Dict, Any

# Ensure data directory exists
DATA_DIR = "data"
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")


def log_task(task: str, duration: float, category: str = None, description: str = None, date: str = None) -> Dict[
    str, Any]:
    """
    Log a task with its duration to persistent storage.

    This function:
    1. Creates the data directory if it doesn't exist
    2. Adds a timestamp to the log entry
    3. Appends the entry to the logs file
    4. Returns the created log entry

    Args:
        task: Name of the task being logged
        duration: Time spent on the task in hours
        category: Optional category of the task (e.g., work, personal, exercise)
        description: Optional description of the task
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        Dict containing the logged entry (task, duration, timestamp, and optional fields)
    """
    # Create data directory if it doesn't exist
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Generate the current timestamp and today's date if needed
    current_timestamp = datetime.datetime.now().isoformat()
    today_date = datetime.date.today().isoformat()

    # Create log entry with required fields
    entry = {
        "task": task,
        "duration": duration,
        "date": date if date else today_date,  # Always include date (today if not provided)
        "timestamp": current_timestamp
    }

    # Add optional fields if provided
    if category:
        entry["category"] = category

    if description:
        entry["description"] = description

    # Load existing logs or create empty list
    try:
        with open(LOGS_FILE, 'r') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    # Append new entry
    logs.append(entry)

    # Write logs back to file
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

    return entry