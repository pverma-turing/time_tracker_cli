"""
Task tracking functionality for the Task Time Tracker application.

This module provides functions to log tasks to persistent storage,
including duration and timestamp information. It handles file operations
and maintains the correct format for task logs.
"""

import os
import json
import datetime
from typing import Dict, Any, Optional

# Ensure data directory exists
DATA_DIR = "data"
DEFAULT_LOGS_FILE = os.path.join(DATA_DIR, "logs.json")


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    """
    default_config = {
        "log_file_path": DEFAULT_LOGS_FILE
    }

    if not config_path:
        return default_config

    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)

        # Merge with default config (to ensure all expected keys exist)
        merged_config = {**default_config, **config_data}
        return merged_config
    except FileNotFoundError:
        raise ValueError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in config file: {config_path}")
    except Exception as e:
        raise ValueError(f"Error loading config file: {str(e)}")


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
    try:
        with open(log_file_path, 'r') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    # Append new entry
    logs.append(entry)

    # Write logs back to file
    with open(log_file_path, 'w') as f:
        json.dump(logs, f, indent=2)

    return entry
