"""
Data models for the Task Time Tracker application.
"""

import datetime
from typing import Optional


class Task:
    """Represents a task in the time tracking system."""

    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description


class TimeEntry:
    """Represents a single time entry for a task."""

    def __init__(self, task_name: str, duration: float, date: Optional[datetime.date] = None,
                 description: Optional[str] = None):
        self.task_name = task_name
        self.duration = duration
        self.date = date or datetime.date.today()
        self.description = description