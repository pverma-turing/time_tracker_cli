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


def log_task(task: str, duration: float, description: str = None, date: str = None) -> Dict[str, Any]:
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

    Returns:
        Dict containing the logged entry (task, duration, timestamp)
    """
    # Create data directory if it doesn't exist
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Create log entry with current timestamp in ISO 8601 format
    timestamp = datetime.datetime.now().isoformat()
    entry = {
        "task": task,
        "duration": duration,
        "timestamp": timestamp
    }
    # Add optional fields if provided
    if description:
        entry["description"] = description

    if date:
        entry["date"] = date

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