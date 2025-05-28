"""
Task tracking functionality for the Task Time Tracker application.

This module provides functions to log tasks to persistent storage,
including duration and timestamp information. It handles file operations
and maintains the correct format for task logs.
"""

import os
import datetime
from typing import Dict, Any, Optional

# Ensure data directory exists
DATA_DIR = "data"
DEFAULT_LOGS_FILE = os.path.join(DATA_DIR, "logs.json")


# Updated function signature to accept config
def log_task(task: str, duration: float, category: str = None, description: str = None,
             date: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
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
    # Validate duration is positive
    if duration <= 0:
        raise ValueError("Duration must be greater than 0.")

    # Trim whitespace from string inputs
    task = task.strip() if task else task
    category = category.strip() if category else category
    description = description.strip() if description else description
    date = date.strip() if date else date

    # Validate task name is not empty after trimming
    if not task:
        raise ValueError("Task name cannot be empty.")

    # Validate date format if provided
    if date:
        try:
            # Try to parse the string as a ISO 8601 date
            parsed_date = datetime.date.fromisoformat(date)
            # Convert back to string to ensure consistent format
            date = parsed_date.isoformat()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")

    # Determine which log file to use
    log_file_path = DEFAULT_LOGS_FILE

    # Use custom path from config if provided
    if config and 'log_file_path' in config:
        custom_path = config['log_file_path']
        # Ensure the directory for the custom path exists
        custom_dir = os.path.dirname(custom_path)
        if custom_dir and not os.path.exists(custom_dir):
            os.makedirs(custom_dir)
        log_file_path = custom_path

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

    entry['_log_file'] = log_file_path
    # Load existing logs or create empty list
    from storage import load_logs, save_logs

    logs = load_logs(log_file_path)
    logs.append(entry)
    save_logs(logs, log_file_path)
    return entry
