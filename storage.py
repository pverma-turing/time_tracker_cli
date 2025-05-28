"""
Storage utilities for the Task Time Tracker application.

This module handles all file operations related to storing and retrieving
task logs. It provides a unified interface for working with log files,
regardless of their location.
"""

import os
import json
from typing import List, Dict, Any, Optional


def load_logs(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load task logs from a JSON file.

    This function:
    1. Checks if the specified file exists
    2. If it exists, loads and parses the JSON content
    3. If it doesn't exist, returns an empty list

    Args:
        file_path: Path to the logs file (defaults to "data/logs.json" if not provided)

    Returns:
        List of task entry dictionaries

    Raises:
        ValueError: If the file exists but contains invalid JSON
    """
    # Use default path if none provided
    if file_path is None:
        data_dir = "data"
        # Ensure data directory exists if using default path
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        file_path = os.path.join(data_dir, "logs.json")

    # If the file doesn't exist, return an empty list
    if not os.path.exists(file_path):
        return []

    # Try to load and parse the JSON file
    try:
        with open(file_path, 'r') as f:
            logs = json.load(f)

        # Validate that the loaded data is a list
        if not isinstance(logs, list):
            raise ValueError(f"Invalid log format in {file_path}. Expected a list of entries.")

        return logs
    except json.JSONDecodeError:
        raise ValueError(f"Cannot parse logs file: {file_path}. The file contains invalid JSON.")


def save_logs(logs: List[Dict[str, Any]], file_path: Optional[str] = None) -> str:
    """
    Save task logs to a JSON file.

    This function:
    1. Ensures the target directory exists
    2. Writes the logs list to the specified file in JSON format

    Args:
        logs: List of log entries to save
        file_path: Path to the logs file (defaults to "data/logs.json" if not provided)

    Returns:
        The path to the file where logs were saved
    """
    # Use default path if none provided
    if file_path is None:
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        file_path = os.path.join(data_dir, "logs.json")

    # Ensure the directory exists
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # Write the logs to the file
    with open(file_path, 'w') as f:
        json.dump(logs, f, indent=2)

    return file_path